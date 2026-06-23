// -----------------------------------------------------------------------------
// pe.sv  --  Processing Element (single MAC) for the MTU systolic array
//
// Weight-stationary design (TPU / Groq style):
//   * Each PE holds one stationary weight in `w_reg`.
//   * Activations flow left -> right  (a_in  -> a_out), one PE per cycle.
//   * Partial sums flow top  -> bottom (psum_in -> psum_out), one PE per cycle.
//   * Weights are loaded by shifting them down a column: during `load_w`,
//     w_reg captures `w_in` (the weight register of the PE above) and exposes
//     it on `w_out` to the PE below.
//
// Per cycle (compute):   psum_out <= psum_in + a_in * w_reg
// This is the canonical multiply-accumulate that, when tiled into an NxN grid
// with diagonally-skewed inputs, evaluates a full matrix multiply.
// -----------------------------------------------------------------------------
`default_nettype none

module pe #(
    parameter int DATA_W = 8,    // operand width (INT8 in Phase 1/2)
    parameter int ACC_W  = 32    // accumulator width (wide enough to avoid overflow)
) (
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       load_w,    // 1 = shift weights down the column
    input  wire signed [DATA_W-1:0]   w_in,      // weight from PE above (load chain)
    output wire signed [DATA_W-1:0]   w_out,     // weight to PE below  (load chain)
    input  wire signed [DATA_W-1:0]   a_in,      // activation from the left
    output reg  signed [DATA_W-1:0]   a_out,     // activation to the right
    input  wire signed [ACC_W-1:0]    psum_in,   // partial sum from above
    output reg  signed [ACC_W-1:0]    psum_out   // partial sum to below
);

    reg signed [DATA_W-1:0] w_reg;

    // The stationary weight is visible to the PE below for the load shift chain.
    assign w_out = w_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            w_reg    <= '0;
            a_out    <= '0;
            psum_out <= '0;
        end else begin
            if (load_w) begin
                w_reg <= w_in;                       // shift weights down one row
            end
            a_out    <= a_in;                        // propagate activation right
            psum_out <= psum_in + (a_in * w_reg);    // MAC, propagate sum down
        end
    end

endmodule

`default_nettype wire
