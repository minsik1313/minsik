// =============================================================================
//  sync_mem_mp.v
//  멀티 포트 데이터 메모리 (GPU 코어용)
//
//  P개의 lane이 같은 사이클에 서로 다른 주소를 동시에 읽고/쓸 수 있도록
//  PORTS개의 독립 포트를 제공한다. (각 lane의 thread-id 기반 주소는 서로
//  겹치지 않으므로 쓰기 충돌은 발생하지 않는다는 전제)
//
//  실제 GPU 의 메모리 컨트롤러/뱅킹/coalescing 을 간략화한 동작 모델이다.
// =============================================================================
`timescale 1ns / 1ps

module sync_mem_mp #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 64,
    parameter integer PORTS = 4
)(
    input  wire                              clk,
    input  wire [PORTS-1:0]                  we,
    input  wire [PORTS*$clog2(DEPTH)-1:0]     addr_flat,
    input  wire [PORTS*WIDTH-1:0]            wdata_flat,
    output wire [PORTS*WIDTH-1:0]            rdata_flat
);

    localparam integer AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    genvar p;
    generate
        for (p = 0; p < PORTS; p = p + 1) begin : RDPORT
            assign rdata_flat[p*WIDTH +: WIDTH] = mem[ addr_flat[p*AW +: AW] ];
        end
    endgenerate

    integer i;
    always @(posedge clk) begin
        for (i = 0; i < PORTS; i = i + 1) begin
            if (we[i])
                mem[ addr_flat[i*AW +: AW] ] <= wdata_flat[i*WIDTH +: WIDTH];
        end
    end

endmodule
