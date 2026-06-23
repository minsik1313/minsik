// =============================================================================
//  cpu_vec.v
//  CPU 스타일 벡터 연산기 (순차 처리 / Sequential)
//
//  단 하나의 MAC(곱셈기) 자원을 사용하여 한 클록에 원소 1개씩 처리한다.
//  N개의 원소를 계산하려면 N 클록이 필요하다.  ->  O(N) cycles
//
//  연산:  C[i] = A[i] * B[i]   (i = 0 .. N-1)
// =============================================================================
`timescale 1ns / 1ps

module cpu_vec #(
    parameter integer N  = 16,   // 벡터 길이 (원소 개수)
    parameter integer DW = 8     // 원소 비트 폭
)(
    input  wire                  clk,
    input  wire                  rst,      // 동기 리셋 (active-high)
    input  wire                  start,    // 1클록 펄스: 연산 시작
    input  wire [N*DW-1:0]       a_flat,   // 입력 벡터 A (flatten)
    input  wire [N*DW-1:0]       b_flat,   // 입력 벡터 B (flatten)
    output reg  [N*2*DW-1:0]     c_flat,   // 출력 벡터 C (flatten, 2*DW 폭)
    output reg                   busy,     // 연산 진행 중
    output reg                   done      // 1클록 펄스: 연산 완료
);

    // ----- 내부 상태 -----
    localparam integer IDXW = (N <= 1) ? 1 : $clog2(N);

    reg [IDXW:0] idx;   // 현재 처리 중인 원소 인덱스 (0..N)

    // 현재 인덱스의 원소 슬라이스
    wire [DW-1:0]   a_elem = a_flat[idx*DW +: DW];
    wire [DW-1:0]   b_elem = b_flat[idx*DW +: DW];
    wire [2*DW-1:0] prod   = a_elem * b_elem;   // 단일 곱셈기

    always @(posedge clk) begin
        if (rst) begin
            idx    <= 0;
            busy   <= 1'b0;
            done   <= 1'b0;
            c_flat <= {N*2*DW{1'b0}};
        end else begin
            done <= 1'b0;                 // 기본값 (펄스)

            if (start && !busy) begin
                // 연산 시작
                idx  <= 0;
                busy <= 1'b1;
            end else if (busy) begin
                // 한 클록에 원소 1개 처리 (순차)
                c_flat[idx*2*DW +: 2*DW] <= prod;

                if (idx == N-1) begin
                    busy <= 1'b0;
                    done <= 1'b1;         // 마지막 원소 계산 완료
                    idx  <= 0;
                end else begin
                    idx <= idx + 1'b1;
                end
            end
        end
    end

endmodule
