# MTU Benchmarks (Phase 5)

This document will hold measured results once Phase 5 (FPGA synthesis +
instrumented simulation) lands. The methodology below defines *how* MTU's claim
of being "competitive with GPU/TPU" is evaluated — on efficiency, not absolute
silicon scale.

## Metrics

| Metric | How measured | Reference points |
|--------|--------------|------------------|
| Peak MACs/cycle | `ROWS × COLS` from RTL params | TPU v7 MXU = 65,536 (256×256) |
| Array utilization % | active-MAC-cycles ÷ (peak × cycles), from sim trace | TPU sustains high util via skewed dataflow |
| Throughput (GEMM) | cycles to finish a tiled GEMM × clock | — |
| Energy / MAC | gate-level / FPGA power ÷ MAC count | weight-stationary minimizes SRAM↔PE movement |
| Area & Fmax | Verilator/yosys + FPGA synthesis reports | scaling curve 16×16 → 256×256 |

## Why efficiency, not PFLOPS

Absolute throughput (B200 ≈ 9 PFLOPS FP4; TPU v7 ≈ 4.6 PFLOPS FP8) is dominated
by process node, die area and HBM bandwidth — not architecture. MTU is evaluated
on **per-MAC efficiency and utilization at a fixed array size**, where a
weight-stationary deterministic dataflow can match or beat general-purpose GPUs.

## Planned experiments

1. Utilization vs. matrix shape (square, tall, wide) at 16×16, 64×64, 256×256.
2. INT8 vs. FP8 vs. BF16 throughput once mixed precision (Phase 4) lands.
3. FPGA Fmax/area scaling curve and energy/op vs. array size.
