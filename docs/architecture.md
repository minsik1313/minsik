# MTU Architecture

MTU (Minsik Tensor Unit) is a weight-stationary systolic tensor accelerator.
This document describes the dataflow and the modules implemented through Phase 2;
later phases (Unified Buffer, controller, vector unit, DMA) wrap this same core.

## Why this design

The 2025–2026 leaders all converge on the same ideas, which MTU adopts:

| Technique | Seen in | MTU choice |
|-----------|---------|------------|
| Systolic array of MACs (massive parallelism + data reuse) | TPU 128×128→256×256 MXU | parameterizable ROWS×COLS PE grid |
| Weight-stationary + on-chip memory next to compute | Groq LPU, TPU | weights held in each PE; activations stream |
| Deterministic, stall-free dataflow | Groq LPU | fixed-latency skewed pipeline |
| Mixed precision (FP4/FP8/BF16/INT8) | B200, TPU v7 Ironwood | INT8 today; FP8/BF16 in Phase 4 |
| Parameterized/configurable generator | Gemmini, MIT LEGO | one RTL, 16×16 → 256×256 |

## Top-level (Phase 0–2)

```
              ┌──────────────── mtu_top ────────────────┐
 w_load_in →  │   ┌──────────────────────────────────┐  │
 a_in      →  │   │     systolic_array (ROWS×COLS)    │  │ → y_out
 load_w    →  │   │      grid of `pe` MAC cells       │  │
              │   └──────────────────────────────────┘  │
              └─────────────────────────────────────────┘
```

## Processing Element (`rtl/pe/pe.sv`)

Each PE holds one stationary weight and performs, per cycle:

```
psum_out <= psum_in + a_in * w_reg      // multiply-accumulate, flows DOWN
a_out    <= a_in                        // activation flows RIGHT
```

Weights are loaded by a vertical shift chain: while `load_w` is high each PE
captures `w_in` (the weight register of the PE above) and exposes it on `w_out`
to the PE below.

## Systolic array (`rtl/mxu/systolic_array.sv`)

A `ROWS × COLS` grid computing `Y[m][n] = Σ_k X[m][k]·W[k][n]`:

- `PE[k][n]` holds the stationary weight `W[k][n]`.
- Activations enter the **left** edge — row `k` carries the contraction index `k`.
- Partial sums accumulate **down** each column; `y_out[n]` is column `n`'s result.
- Top partial-sum inputs are tied to 0; the array self-flushes between tiles.

Ports are **flattened packed vectors** (`a_in[ROWS*DATA_W-1:0]`,
`y_out[COLS*ACC_W-1:0]`) so any simulator and cocotb can drive them as integers.

### Dataflow timing

The grid requires diagonally skewed I/O (handled by the testbench / future
controller, mirrored in `model/golden.py`):

| Event | Cycle |
|-------|-------|
| Weight load (per column `n`): feed `W[K-1][n] … W[0][n]` | `0 … K-1`, `load_w=1` |
| Activation `X[m][k]` enters row `k` | `m + k` |
| Output `Y[m][n]` appears on `y_out[n]` | `ROWS + m + n` |

`ROWS` cycles of latency come from one MAC-register stage per array row plus the
synchronous drive-to-capture cycle of the testbench. Throughput is one full
`COLS`-wide output row per cycle once the pipeline is primed → peak
`ROWS × COLS` MACs/cycle (e.g. 65,536 MACs/cycle at 256×256, matching the TPU
v6/v7 MXU).

## Verification

`model/golden.py` provides the integer matmul reference plus the
`weight_load_seq` / `skew_inputs` / `deskew_outputs` helpers. Every cocotb test
(`tb/`) drives real GEMMs and asserts **bit-exact** equality with numpy. CI runs
Verilator lint + the full suite on every push (`.github/workflows/ci.yml`).

## Roadmap (next phases)

- **Phase 3** — `unified_buffer.sv` (double-buffered SRAM) + `controller.sv`
  decoding a mini-ISA (`LOAD_W`, `MATMUL`, `ACT`, `STORE`); tiling for matrices
  larger than the array. See [`isa.md`](isa.md).
- **Phase 4** — `vector_unit.sv` (ReLU/GELU, bias, requantization) and a
  mixed-precision PE (`PRECISION_MODE` ∈ INT8/FP8/BF16).
- **Phase 5** — `axi_dma.sv`, FPGA synthesis (timing/area), and
  utilization/energy benchmarks vs. GPU/TPU in [`benchmarks.md`](benchmarks.md).
