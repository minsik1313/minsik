// =============================================================================
//  gpu_core.v
//  SIMT(Single Instruction, Multiple Threads) 방식 GPU 코어
//
//  cpu_core.v 와 동일한 ISA/디코더를 P개의 lane(스레드)에 공유한다.
//  - 명령어 fetch/decode 는 단 한 번만 수행되어 모든 lane 에 동시에 방송된다.
//  - 각 lane 은 자신만의 레지스터 파일을 가지며, r0 은 하드웨어가 블록
//    시작 시 자동으로 채워주는 thread-id 전용 레지스터다.
//  - 커널 프로그램에는 분기/루프 명령어가 없다 (실제 GPU 가 스레드 인덱싱으로
//    루프를 대체하는 것과 동일한 방식). N > P 인 경우 "블록" 단위로 커널을
//    반복 실행해 나머지 원소를 처리한다.
// =============================================================================
`timescale 1ns / 1ps
`include "../common/isa_defs.vh"

module gpu_core #(
    parameter integer N          = 16,   // 벡터 길이
    parameter integer P          = 4,    // 병렬 lane(스레드) 수
    parameter integer IMEM_DEPTH = 16,   // 커널 명령어 메모리 깊이
    parameter integer DMEM_DEPTH = 3*N   // 데이터 메모리 깊이 (A,B,C 영역)
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg          busy,
    output reg          done,
    output reg [31:0]   cycle_count,
    output reg [31:0]   instr_count,   // 완료한 "명령어 슬롯" 수 (블록 x lane 합산 아님, 발행 횟수)

    // 외부 멀티포트 데이터 메모리(sync_mem_mp, PORTS=P) 와의 연결
    output reg  [P-1:0]                       dmem_we,
    output reg  [P*$clog2(DMEM_DEPTH)-1:0]     dmem_addr_flat,
    output reg  [P*32-1:0]                    dmem_wdata_flat,
    input  wire [P*32-1:0]                    dmem_rdata_flat
);

    localparam integer AW   = (IMEM_DEPTH <= 1) ? 1 : $clog2(IMEM_DEPTH);
    localparam integer DAW  = $clog2(DMEM_DEPTH);
    localparam integer NBLK = (N + P - 1) / P;     // 처리할 블록(=커널 실행) 수
    localparam integer BCW  = (NBLK <= 1) ? 1 : $clog2(NBLK+1);

    // ----- 커널 명령어 메모리 (모든 lane 공유) -----
    reg [31:0] imem [0:IMEM_DEPTH-1];

    function [31:0] enc(input [3:0] op, input [3:0] rd, input [3:0] rs1,
                         input [3:0] rs2, input [15:0] imm);
        enc = {op, rd, rs1, rs2, imm};
    endfunction

    integer ii;
    initial begin
        for (ii = 0; ii < IMEM_DEPTH; ii = ii + 1)
            imem[ii] = enc(`OP_NOP, 0,0,0, 0);

        // ---- 커널: C[tid] = A[tid] * B[tid]; (분기/루프 없음) ----
        // r0 = tid (하드웨어가 블록 시작 시 자동 적재), r1=A[tid], r2=B[tid], r3=product
        imem[0] = enc(`OP_LW,  1, 0, 0, 16'd0);     // r1 = MEM[tid+0]   (A[tid])
        imem[1] = enc(`OP_LW,  2, 0, 0, N);          // r2 = MEM[tid+N]   (B[tid])
        imem[2] = enc(`OP_MUL, 3, 1, 2, 16'd0);      // r3 = r1 * r2
        imem[3] = enc(`OP_SW,  0, 0, 3, 2*N);        // MEM[tid+2N] = r3  (C[tid])
        imem[4] = enc(`OP_HALT,0, 0, 0, 16'd0);
    end

    // ----- lane 별 레지스터 파일 (P x 16 x 32bit) -----
    reg [31:0] regs [0:P-1][0:15];

    reg [AW-1:0]  pc;
    reg [31:0]    ir;
    reg [BCW-1:0] blk;          // 현재 블록 인덱스

    wire [3:0]  op  = ir[31:28];
    wire [3:0]  rd  = ir[27:24];
    wire [3:0]  rs1 = ir[23:20];
    wire [3:0]  rs2 = ir[19:16];
    wire [31:0] imm = {{16{ir[15]}}, ir[15:0]};

    // ----- 단계 간 래치 -----
    reg [31:0] alu_res_r  [0:P-1];
    reg [31:0] mem_addr_r [0:P-1];
    reg [31:0] store_data_r [0:P-1];
    reg [3:0]  rd_r, op_r;

    // lane 별 ALU 결과를 런타임 인덱스로 접근하기 위해 실제 배열(unpacked array)로
    // 노출한다 (generate 블록의 이름 스코프는 상수 인덱스만 허용되므로 procedural
    // for 문에서 바로 참조할 수 없다).
    wire [31:0] lane_alu_result [0:P-1];
    wire [31:0] lane_eff_addr   [0:P-1];
    wire [31:0] lane_rs2_val    [0:P-1];

    genvar g;
    generate
        for (g = 0; g < P; g = g + 1) begin : LANE
            wire [31:0] rs1_val = regs[g][rs1];
            wire [31:0] rs2_val = regs[g][rs2];

            wire [31:0] alu_add  = rs1_val + rs2_val;
            wire [31:0] alu_sub  = rs1_val - rs2_val;
            wire [31:0] alu_mul  = rs1_val * rs2_val;
            wire [31:0] alu_addi = rs1_val + imm;
            wire [31:0] alu_li   = imm;

            wire [31:0] alu_result = (op == `OP_ADD)  ? alu_add  :
                                      (op == `OP_SUB)  ? alu_sub  :
                                      (op == `OP_MUL)  ? alu_mul  :
                                      (op == `OP_ADDI) ? alu_addi :
                                      (op == `OP_LI)   ? alu_li   : 32'd0;

            wire [31:0] eff_addr = rs1_val + imm;

            assign lane_alu_result[g] = alu_result;
            assign lane_eff_addr[g]   = eff_addr;
            assign lane_rs2_val[g]    = rs2_val;
        end
    endgenerate

    // ----- FSM -----
    localparam ST_IDLE       = 0,
               ST_BLOCK_INIT = 1,
               ST_FETCH      = 2,
               ST_EXEC       = 3,
               ST_MEM        = 4,
               ST_WB         = 5,
               ST_HALT       = 6;

    reg [2:0] state;
    integer l, rr;

    always @(posedge clk) begin
        if (rst) begin
            state       <= ST_IDLE;
            pc          <= 0;
            blk         <= 0;
            busy        <= 1'b0;
            done        <= 1'b0;
            cycle_count <= 0;
            instr_count <= 0;
            dmem_we         <= {P{1'b0}};
            dmem_addr_flat  <= 0;
            dmem_wdata_flat <= 0;
            for (l = 0; l < P; l = l + 1)
                for (rr = 0; rr < 16; rr = rr + 1)
                    regs[l][rr] <= 0;
        end else begin
            dmem_we <= {P{1'b0}};
            done    <= 1'b0;

            if (busy) cycle_count <= cycle_count + 1;

            case (state)
                ST_IDLE: begin
                    if (start) begin
                        blk   <= 0;
                        busy  <= 1'b1;
                        state <= ST_BLOCK_INIT;
                    end
                end

                // 블록 시작: 각 lane 의 r0(tid) 을 하드웨어가 자동으로 채움
                ST_BLOCK_INIT: begin
                    for (l = 0; l < P; l = l + 1)
                        regs[l][0] <= blk * P + l;   // tid = blockBase + laneIndex
                    pc    <= 0;
                    state <= ST_FETCH;
                end

                ST_FETCH: begin
                    ir    <= imem[pc];
                    pc    <= pc + 1'b1;
                    state <= ST_EXEC;
                end

                ST_EXEC: begin
                    for (l = 0; l < P; l = l + 1) begin
                        alu_res_r[l]    <= lane_alu_result[l];
                        mem_addr_r[l]   <= lane_eff_addr[l];
                        store_data_r[l] <= lane_rs2_val[l];
                    end
                    rd_r  <= rd;
                    op_r  <= op;
                    state <= ST_MEM;
                end

                ST_MEM: begin
                    for (l = 0; l < P; l = l + 1) begin
                        if (op_r == `OP_LW) begin
                            // 이 lane 의 thread-id 가 N 범위를 벗어나면 접근 생략
                            if (blk*P + l < N) begin
                                dmem_addr_flat[l*DAW +: DAW] <= mem_addr_r[l][DAW-1:0];
                            end
                            dmem_we[l] <= 1'b0;
                        end else if (op_r == `OP_SW) begin
                            if (blk*P + l < N) begin
                                dmem_addr_flat[l*DAW +: DAW]  <= mem_addr_r[l][DAW-1:0];
                                dmem_wdata_flat[l*32 +: 32]   <= store_data_r[l];
                                dmem_we[l]                    <= 1'b1;
                            end
                        end
                    end
                    state <= ST_WB;
                end

                ST_WB: begin
                    for (l = 0; l < P; l = l + 1) begin
                        case (op_r)
                            `OP_ADD, `OP_SUB, `OP_MUL, `OP_ADDI, `OP_LI:
                                regs[l][rd_r] <= alu_res_r[l];
                            `OP_LW:
                                regs[l][rd_r] <= dmem_rdata_flat[l*32 +: 32];
                            default: ;
                        endcase
                    end

                    instr_count <= instr_count + 1'b1;   // 블록당 발행된 명령어 슬롯 수

                    if (op_r == `OP_HALT) begin
                        if (blk == NBLK-1) begin
                            busy  <= 1'b0;
                            done  <= 1'b1;
                            state <= ST_IDLE;
                        end else begin
                            blk   <= blk + 1'b1;
                            state <= ST_BLOCK_INIT;
                        end
                    end else begin
                        state <= ST_FETCH;
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
