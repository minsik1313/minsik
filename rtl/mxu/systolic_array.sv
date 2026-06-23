// -----------------------------------------------------------------------------
// systolic_array.sv  --  MXU: ROWS x COLS weight-stationary systolic array
//
// Computes  Y[m][n] = sum_k  X[m][k] * W[k][n]   where
//   * W is (ROWS x COLS): PE[k][n] holds the stationary weight W[k][n].
//   * X activations enter the LEFT edge, one stream per row (contraction idx k).
//   * Y partial sums exit the BOTTOM edge, one accumulator per column n.
//
// Dataflow / timing (driven by the testbench / controller):
//   - Weights are loaded by shifting each column down: feed column n with
//     W[ROWS-1][n], W[ROWS-2][n], ... , W[0][n] over ROWS cycles with load_w=1.
//   - Activations are fed diagonally skewed: X[m][k] enters row k at cycle m+k.
//   - Output Y[m][n] emerges at the bottom of column n skewed by (m+n).
// The companion Python golden model (model/golden.py) performs the same skew so
// RTL results can be compared bit-exactly.
//
// Ports use FLATTENED packed vectors (not SV unpacked arrays) so that cocotb and
// every simulator can drive/sample them as plain integers.
// -----------------------------------------------------------------------------
`default_nettype none

module systolic_array #(
    parameter int ROWS   = 4,    // contraction dimension K (array height)
    parameter int COLS   = 4,    // output dimension      N (array width)
    parameter int DATA_W = 8,
    parameter int ACC_W  = 32
) (
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          load_w,
    // Weight load: one DATA_W operand per column, fed into the top of each column.
    input  wire [COLS*DATA_W-1:0]        w_load_in,
    // Activations: one DATA_W operand per row, fed into the left of each row.
    input  wire [ROWS*DATA_W-1:0]        a_in,
    // Outputs: one ACC_W accumulator per column, from the bottom of each column.
    output wire [COLS*ACC_W-1:0]         y_out
);

    // Interconnect meshes between PEs.
    //   a_h[r][c]   : activation entering PE[r][c] from the left   (a_h[r][0] = a_in row r)
    //   w_v[r][c]   : weight     entering PE[r][c] from above      (w_v[0][c] = w_load_in col c)
    //   p_v[r][c]   : partial sum entering PE[r][c] from above     (p_v[0][c] = 0)
    wire signed [DATA_W-1:0] a_h [ROWS][COLS+1];
    wire signed [DATA_W-1:0] w_v [ROWS+1][COLS];
    wire signed [ACC_W-1:0]  p_v [ROWS+1][COLS];

    genvar r, c;
    generate
        // Left-edge activation inputs.
        for (r = 0; r < ROWS; r++) begin : g_a_edge
            assign a_h[r][0] = a_in[r*DATA_W +: DATA_W];
        end
        // Top-edge weight-load and zero partial-sum inputs.
        for (c = 0; c < COLS; c++) begin : g_top_edge
            assign w_v[0][c] = w_load_in[c*DATA_W +: DATA_W];
            assign p_v[0][c] = '0;
        end
        // The PE grid.
        for (r = 0; r < ROWS; r++) begin : g_row
            for (c = 0; c < COLS; c++) begin : g_col
                pe #(
                    .DATA_W (DATA_W),
                    .ACC_W  (ACC_W)
                ) u_pe (
                    .clk      (clk),
                    .rst_n    (rst_n),
                    .load_w   (load_w),
                    .w_in     (w_v[r][c]),
                    .w_out    (w_v[r+1][c]),
                    .a_in     (a_h[r][c]),
                    .a_out    (a_h[r][c+1]),
                    .psum_in  (p_v[r][c]),
                    .psum_out (p_v[r+1][c])
                );
            end
        end
        // Bottom-edge accumulator outputs.
        for (c = 0; c < COLS; c++) begin : g_y_edge
            assign y_out[c*ACC_W +: ACC_W] = p_v[ROWS][c];
        end
    endgenerate

endmodule

`default_nettype wire
