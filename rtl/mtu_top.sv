// -----------------------------------------------------------------------------
// mtu_top.sv  --  MTU (Minsik Tensor Unit) top level
//
// Phase 0-2 scope: a thin wrapper exposing the weight-stationary systolic MXU
// as the compute core of the accelerator. Later phases (per the design plan)
// add the Unified Buffer, mini-ISA Controller, Vector/Special-Function Unit and
// the AXI4/DMA front-end around this same core.
//
// Parameters scale the array from FPGA-sized (e.g. 16x16) up to ASIC-class
// (256x256, matching TPU-v6/v7 MXU dimensions) without changing the RTL.
// -----------------------------------------------------------------------------
`default_nettype none

module mtu_top #(
    parameter int ARRAY_ROWS = 16,   // contraction dim K
    parameter int ARRAY_COLS = 16,   // output dim N
    parameter int DATA_W     = 8,    // INT8 today; FP8/BF16 modes land in Phase 4
    parameter int ACC_W      = 32
) (
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire                              load_w,
    input  wire [ARRAY_COLS*DATA_W-1:0]      w_load_in,
    input  wire [ARRAY_ROWS*DATA_W-1:0]      a_in,
    output wire [ARRAY_COLS*ACC_W-1:0]       y_out
);

    systolic_array #(
        .ROWS   (ARRAY_ROWS),
        .COLS   (ARRAY_COLS),
        .DATA_W (DATA_W),
        .ACC_W  (ACC_W)
    ) u_mxu (
        .clk       (clk),
        .rst_n     (rst_n),
        .load_w    (load_w),
        .w_load_in (w_load_in),
        .a_in      (a_in),
        .y_out     (y_out)
    );

endmodule

`default_nettype wire
