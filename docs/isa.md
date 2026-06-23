# MTU Mini-ISA (Phase 3 design)

The Phase 3 controller (`rtl/ctrl/controller.sv`) decodes a small, fixed-length
instruction stream that sequences the array, Unified Buffer and (Phase 4) vector
unit. This document is the design target; the controller RTL lands in Phase 3.

## Instruction format (64-bit, draft)

```
 63        56 55                      24 23                    0
+------------+---------------------------+----------------------+
|  opcode(8) |       operand A (32)      |     operand B (24)   |
+------------+---------------------------+----------------------+
```

## Opcodes (draft)

| Opcode    | Operands | Action |
|-----------|----------|--------|
| `LOAD_W`  | ub_addr, tile_id | Shift a `ROWS×COLS` weight tile from the Unified Buffer into the array. |
| `MATMUL`  | act_addr, m_rows | Stream `m_rows` activation rows (skewed) through the array. |
| `ACT`     | mode, scale | Apply activation/bias/requantization via the vector unit (Phase 4). |
| `STORE`   | ub_addr, m_rows | Write results back to the Unified Buffer. |
| `SYNC`    | — | Barrier between double-buffered tiles. |

## Tiling

Matrices larger than the array are tiled into `ROWS×COLS` blocks. The Unified
Buffer is double-buffered so the next weight/activation tile loads while the
current one computes — keeping the array stall-free (Groq-style deterministic
dataflow) and utilization high.
