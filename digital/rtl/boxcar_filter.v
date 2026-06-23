// boxcar_filter.v
//
// N-tap moving-average (boxcar) FIR filter — the digital backend block of the
// sensor front-end SoC (see docs/FABLESS_PLAN.md §2.9 target circuit).
//
// Running-sum implementation: O(1) per sample regardless of tap count.
// TAPS = 2**LOG2_TAPS so the divide-by-TAPS is a cheap right shift.
//
// This is the small reference block used to bring up and trust the
// open-source RTL->GDS flow (OpenLane2) and the cocotb regression.

module boxcar_filter #(
    parameter integer DATA_WIDTH = 8,
    parameter integer LOG2_TAPS  = 3   // TAPS = 8
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    in_valid,
    input  wire [DATA_WIDTH-1:0]   in_data,
    output reg                     out_valid,
    output reg  [DATA_WIDTH-1:0]   out_data
);
    localparam integer TAPS      = (1 << LOG2_TAPS);
    localparam integer ACC_WIDTH = DATA_WIDTH + LOG2_TAPS;

    reg [DATA_WIDTH-1:0] taps [0:TAPS-1];
    reg [ACC_WIDTH-1:0]  acc;
    integer i;

    // Combinational next-sum: add new sample, drop the oldest tap.
    wire [ACC_WIDTH-1:0] next_acc = acc + in_data - taps[TAPS-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < TAPS; i = i + 1)
                taps[i] <= {DATA_WIDTH{1'b0}};
            acc       <= {ACC_WIDTH{1'b0}};
            out_valid <= 1'b0;
            out_data  <= {DATA_WIDTH{1'b0}};
        end else begin
            out_valid <= 1'b0;
            if (in_valid) begin
                acc <= next_acc;
                for (i = TAPS-1; i > 0; i = i - 1)
                    taps[i] <= taps[i-1];
                taps[0]   <= in_data;
                out_data  <= next_acc >> LOG2_TAPS;  // average = sum / TAPS
                out_valid <= 1'b1;
            end
        end
    end
endmodule
