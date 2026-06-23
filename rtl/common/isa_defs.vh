// =============================================================================
//  isa_defs.vh
//  CPU/GPU 코어가 공유하는 간단한 ISA(명령어 집합) 정의
//
//  명령어 포맷 (32비트, 고정 길이):
//    [31:28] opcode   [27:24] rd   [23:20] rs1   [19:16] rs2   [15:0] imm(signed)
//
//  레지스터: r0..r15 (32비트). GPU 코어에서는 r0 을 하드웨어가 부여하는
//  thread-id 전용 레지스터로 사용한다 (블록 시작 시 자동 로드).
// =============================================================================
`ifndef ISA_DEFS_VH
`define ISA_DEFS_VH

`define OP_NOP   4'h0
`define OP_ADD   4'h1   // rd = rs1 + rs2
`define OP_SUB   4'h2   // rd = rs1 - rs2
`define OP_MUL   4'h3   // rd = rs1 * rs2
`define OP_ADDI  4'h4   // rd = rs1 + imm
`define OP_LI    4'h5   // rd = imm
`define OP_LW    4'h6   // rd = MEM[rs1 + imm]
`define OP_SW    4'h7   // MEM[rs1 + imm] = rs2
`define OP_BNE   4'h8   // if (rs1 != rs2) pc += imm   (imm: 다음 PC 기준 상대 오프셋)
`define OP_HALT  4'hF   // 실행 종료

`endif
