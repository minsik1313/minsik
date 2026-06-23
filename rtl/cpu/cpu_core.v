// =============================================================================
//  cpu_core.v
//  멀티사이클 스칼라 CPU 코어 (실제 CPU 구조에 가깝게 구현한 버전)
//
//  PC -> 명령어 메모리 fetch -> decode -> execute(ALU) -> memory -> writeback
//  의 4단계를 명령어 1개당 4클록에 걸쳐 순차적으로 수행한다.
//  (파이프라이닝 없이 한 번에 한 명령어씩 처리 = 고전적인 multicycle 구조)
//
//  벡터 곱셈 C[i]=A[i]*B[i] 프로그램을 분기(BNE)로 N번 반복하는
//  "소프트웨어 루프"를 실제 명령어로 실행한다. (이전 cpu_vec.v 와의 차이점:
//  여기서는 인덱스 증가/종료 조건 판단도 전부 명령어로 수행된다)
// =============================================================================
`timescale 1ns / 1ps
`include "../common/isa_defs.vh"

module cpu_core #(
    parameter integer N          = 16,   // 벡터 길이
    parameter integer IMEM_DEPTH = 32,   // 명령어 메모리 깊이
    parameter integer DMEM_DEPTH = 3*N   // 데이터 메모리 깊이 (A,B,C 영역, N에 비례)
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg          busy,
    output reg          done,
    output reg [31:0]   cycle_count,   // 시작~완료까지 소요 클록 수
    output reg [31:0]   instr_count,   // 실행한 명령어 수

    // 외부 데이터 메모리(sync_mem) 와의 단일 포트 연결
    output reg                          dmem_we,
    output reg  [$clog2(DMEM_DEPTH)-1:0] dmem_addr,
    output reg  [31:0]                  dmem_wdata,
    input  wire [31:0]                  dmem_rdata
);

    localparam integer AW = (IMEM_DEPTH <= 1) ? 1 : $clog2(IMEM_DEPTH);

    // ----- 명령어 메모리 (ROM, 시뮬레이션 초기화 시 프로그램 적재) -----
    reg [31:0] imem [0:IMEM_DEPTH-1];

    // 간단한 "어셈블러" 함수: opcode/rd/rs1/rs2/imm 을 32비트 명령어로 인코딩
    function [31:0] enc(input [3:0] op, input [3:0] rd, input [3:0] rs1,
                         input [3:0] rs2, input [15:0] imm);
        enc = {op, rd, rs1, rs2, imm};
    endfunction

    integer p;
    initial begin
        for (p = 0; p < IMEM_DEPTH; p = p + 1)
            imem[p] = enc(`OP_NOP, 0,0,0, 0);

        // ---- 프로그램: for (i=0; i<N; i++) C[i] = A[i]*B[i]; ----
        // 데이터 메모리 배치 : A=[0..N-1], B=[N..2N-1], C=[2N..3N-1]
        // r1=i, r2=N(루프 한계), r3=A[i], r4=B[i], r5=product
        imem[0] = enc(`OP_LI,   1, 0, 0, 16'd0);          // r1 = 0            (i=0)
        imem[1] = enc(`OP_LI,   2, 0, 0, N);               // r2 = N
        imem[2] = enc(`OP_LW,   3, 1, 0, 16'd0);           // r3 = MEM[r1+0]    (A[i])
        imem[3] = enc(`OP_LW,   4, 1, 0, N);               // r4 = MEM[r1+N]    (B[i])
        imem[4] = enc(`OP_MUL,  5, 3, 4, 16'd0);           // r5 = r3 * r4
        imem[5] = enc(`OP_SW,   0, 1, 5, 2*N);             // MEM[r1+2N] = r5   (C[i])
        imem[6] = enc(`OP_ADDI, 1, 1, 0, 16'd1);           // r1 = r1 + 1
        imem[7] = enc(`OP_BNE,  0, 1, 2, -16'sd6);          // i!=N -> pc = pc + (-6)  => imm2
        imem[8] = enc(`OP_HALT,0, 0, 0, 16'd0);            // 종료
    end

    // ----- 레지스터 파일 -----
    reg [31:0] regs [0:15];

    // ----- 파이프라인 래치 (단계 간 전달용) -----
    reg [AW-1:0] pc;
    reg [31:0]   ir;                 // fetch 된 명령어
    reg [31:0]   alu_res_r;
    reg [31:0]   mem_addr_r;
    reg [31:0]   store_data_r;
    reg [3:0]    rd_r, op_r;
    reg          branch_taken_r;
    reg [31:0]   branch_target_r;

    // 현재 명령어(ir) decode
    wire [3:0]  op   = ir[31:28];
    wire [3:0]  rd   = ir[27:24];
    wire [3:0]  rs1  = ir[23:20];
    wire [3:0]  rs2  = ir[19:16];
    wire [31:0] imm  = {{16{ir[15]}}, ir[15:0]};

    wire [31:0] rs1_val = regs[rs1];
    wire [31:0] rs2_val = regs[rs2];

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

    wire [31:0] eff_addr   = rs1_val + imm;          // LW/SW 유효 주소
    wire        br_taken   = (op == `OP_BNE) && (rs1_val != rs2_val);

    // ----- FSM 상태 -----
    localparam ST_IDLE  = 0,
               ST_FETCH  = 1,
               ST_EXEC   = 2,
               ST_MEM    = 3,
               ST_WB     = 4,
               ST_HALT   = 5;

    reg [2:0] state;

    integer r;
    always @(posedge clk) begin
        if (rst) begin
            state        <= ST_IDLE;
            pc           <= 0;
            busy         <= 1'b0;
            done         <= 1'b0;
            cycle_count  <= 0;
            instr_count  <= 0;
            dmem_we      <= 1'b0;
            dmem_addr    <= 0;
            dmem_wdata   <= 0;
            for (r = 0; r < 16; r = r + 1) regs[r] <= 0;
        end else begin
            dmem_we <= 1'b0;     // 기본값: 메모리 쓰기 비활성
            done    <= 1'b0;

            if (busy) cycle_count <= cycle_count + 1;

            case (state)
                ST_IDLE: begin
                    if (start) begin
                        pc    <= 0;
                        busy  <= 1'b1;
                        state <= ST_FETCH;
                    end
                end

                ST_FETCH: begin
                    ir    <= imem[pc];
                    pc    <= pc + 1'b1;          // 분기 없을 경우 다음 명령어
                    state <= ST_EXEC;
                end

                ST_EXEC: begin
                    // ir 은 이미 이전 사이클에 래치됨 -> 여기서 조합적으로 decode/ALU 계산된
                    // alu_result/eff_addr/br_taken 값을 다음 단계로 래치
                    alu_res_r       <= alu_result;
                    mem_addr_r      <= eff_addr;
                    store_data_r    <= rs2_val;
                    rd_r            <= rd;
                    op_r            <= op;
                    branch_taken_r  <= br_taken;
                    branch_target_r <= pc + imm;   // pc 는 fetch 단계에서 이미 +1 된 상태(다음 명령어 주소)
                    state           <= ST_MEM;
                end

                ST_MEM: begin
                    if (op_r == `OP_LW) begin
                        dmem_addr <= mem_addr_r[$clog2(DMEM_DEPTH)-1:0];
                        dmem_we   <= 1'b0;
                    end else if (op_r == `OP_SW) begin
                        dmem_addr  <= mem_addr_r[$clog2(DMEM_DEPTH)-1:0];
                        dmem_wdata <= store_data_r;
                        dmem_we    <= 1'b1;
                    end
                    state <= ST_WB;
                end

                ST_WB: begin
                    case (op_r)
                        `OP_ADD, `OP_SUB, `OP_MUL, `OP_ADDI, `OP_LI:
                            regs[rd_r] <= alu_res_r;
                        `OP_LW:
                            regs[rd_r] <= dmem_rdata;   // sync_mem 은 조합적 read -> 바로 사용 가능
                        `OP_BNE: begin
                            if (branch_taken_r) pc <= branch_target_r[AW-1:0];
                        end
                        default: ; // SW, NOP, HALT: 레지스터 갱신 없음
                    endcase

                    instr_count <= instr_count + 1'b1;

                    if (op_r == `OP_HALT) begin
                        busy  <= 1'b0;
                        done  <= 1'b1;
                        state <= ST_IDLE;
                    end else begin
                        state <= ST_FETCH;
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
