// 간단한 8비트 ALU (조합) — RTL 시뮬/합성 데모용
module alu #(parameter W = 8) (
    input  [W-1:0] a,
    input  [W-1:0] b,
    input  [2:0]   op,
    output reg [W-1:0] y,
    output         carry
);
    reg [W:0] tmp;
    always @* begin
        case (op)
            3'b000: tmp = a + b;          // ADD
            3'b001: tmp = a - b;          // SUB
            3'b010: tmp = a & b;          // AND
            3'b011: tmp = a | b;          // OR
            3'b100: tmp = a ^ b;          // XOR
            3'b101: tmp = a << 1;         // SHL
            3'b110: tmp = a >> 1;         // SHR
            default: tmp = {1'b0, a};     // PASS
        endcase
        y = tmp[W-1:0];
    end
    assign carry = tmp[W];
endmodule
