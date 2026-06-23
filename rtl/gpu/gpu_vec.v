// =============================================================================
//  gpu_vec.v
//  GPU 스타일 벡터 연산기 (병렬 처리 / SIMD)
//
//  P개의 PE(Processing Element = 곱셈기)를 병렬로 배치하여
//  한 클록에 원소 P개씩 동시에 처리한다.
//  N개의 원소를 계산하려면 ceil(N/P) 클록이 필요하다.  ->  O(N/P) cycles
//
//  연산:  C[i] = A[i] * B[i]   (CPU 버전과 결과 동일)
// =============================================================================
`timescale 1ns / 1ps

module gpu_vec #(
    parameter integer N  = 16,   // 벡터 길이 (원소 개수)
    parameter integer DW = 8,    // 원소 비트 폭
    parameter integer P  = 4     // 병렬 PE 개수 (lane 수)
)(
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  start,
    input  wire [N*DW-1:0]       a_flat,
    input  wire [N*DW-1:0]       b_flat,
    output reg  [N*2*DW-1:0]     c_flat,
    output reg                   busy,
    output reg                   done
);

    // 처리해야 할 그룹(=클록) 수 = ceil(N / P)
    localparam integer NGROUP = (N + P - 1) / P;
    localparam integer GIDXW  = (NGROUP <= 1) ? 1 : $clog2(NGROUP);

    reg [GIDXW:0] grp;   // 현재 처리 중인 그룹 인덱스 (0..NGROUP)

    // ----- P개의 PE를 병렬로 인스턴스화 -----
    // base = grp*P 부터 P개의 원소를 동시에 계산
    wire [2*DW-1:0] prod [0:P-1];
    genvar k;
    generate
        for (k = 0; k < P; k = k + 1) begin : LANE
            // 이번 그룹에서 이 lane 이 담당하는 전역 인덱스
            wire [31:0]     gi   = grp * P + k;
            // 범위를 벗어나는 lane 은 0 으로 (N 이 P 의 배수가 아닐 때)
            wire [DW-1:0]   a_in = (gi < N) ? a_flat[gi*DW +: DW] : {DW{1'b0}};
            wire [DW-1:0]   b_in = (gi < N) ? b_flat[gi*DW +: DW] : {DW{1'b0}};
            assign prod[k] = a_in * b_in;   // 병렬 곱셈기
        end
    endgenerate

    integer j;
    always @(posedge clk) begin
        if (rst) begin
            grp    <= 0;
            busy   <= 1'b0;
            done   <= 1'b0;
            c_flat <= {N*2*DW{1'b0}};
        end else begin
            done <= 1'b0;

            if (start && !busy) begin
                grp  <= 0;
                busy <= 1'b1;
            end else if (busy) begin
                // 한 클록에 P개 원소 동시 기록 (병렬)
                for (j = 0; j < P; j = j + 1) begin
                    if (grp*P + j < N)
                        c_flat[(grp*P + j)*2*DW +: 2*DW] <= prod[j];
                end

                if (grp == NGROUP-1) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    grp  <= 0;
                end else begin
                    grp <= grp + 1'b1;
                end
            end
        end
    end

endmodule
