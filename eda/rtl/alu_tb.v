// alu 랜덤 테스트벤치 — SEED 로 시드 변경 (리그레션용)
//   iverilog -g2012 -DSEED=<n> alu_tb.v alu.v -o sim && vvp sim
`timescale 1ns/1ps
module alu_tb;
    localparam W = 8;
    reg  [W-1:0] a, b;
    reg  [2:0]   op;
    wire [W-1:0] y;
    wire         carry;

    alu #(.W(W)) dut (.a(a), .b(b), .op(op), .y(y), .carry(carry));

`ifndef SEED
 `define SEED 1
`endif

    integer i, seed, errors;
    reg [W:0] expect_full;

    initial begin
        seed = `SEED;
        errors = 0;
        for (i = 0; i < 1000; i = i + 1) begin
            a  = $random(seed);
            b  = $random(seed);
            op = $random(seed);
            #1;
            case (op)
                3'b000: expect_full = a + b;
                3'b001: expect_full = a - b;
                3'b010: expect_full = a & b;
                3'b011: expect_full = a | b;
                3'b100: expect_full = a ^ b;
                3'b101: expect_full = a << 1;
                3'b110: expect_full = a >> 1;
                default: expect_full = {1'b0, a};
            endcase
            if (y !== expect_full[W-1:0]) begin
                errors = errors + 1;
                $display("MISMATCH seed=%0d a=%h b=%h op=%b y=%h exp=%h",
                         seed, a, b, op, y, expect_full[W-1:0]);
            end
        end
        if (errors == 0)
            $display("PASS seed=%0d (1000 vectors)", seed);
        else
            $display("FAIL seed=%0d errors=%0d", seed, errors);
        $finish;
    end
endmodule
