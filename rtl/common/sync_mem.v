// =============================================================================
//  sync_mem.v
//  단일 포트 데이터 메모리 (CPU 코어용)
//  - 쓰기: 동기 (posedge clk, we=1일 때)
//  - 읽기: 비동기/조합 (주소 인가 즉시 rdata 에 반영)
// =============================================================================
`timescale 1ns / 1ps

module sync_mem #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 64
)(
    input  wire                       clk,
    input  wire                       we,
    input  wire [$clog2(DEPTH)-1:0]   addr,
    input  wire [WIDTH-1:0]           wdata,
    output wire [WIDTH-1:0]           rdata
);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    assign rdata = mem[addr];

    always @(posedge clk) begin
        if (we)
            mem[addr] <= wdata;
    end

endmodule
