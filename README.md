# MTU — Minsik Tensor Unit

A from-scratch **AI accelerator in SystemVerilog RTL**, built in the same
architectural class as modern tensor processors (Google TPU v6/v7, NVIDIA
Blackwell Tensor Cores, Groq LPU): a **weight-stationary systolic array** that
keeps weights on-chip next to the compute and streams activations through a
deterministic dataflow.

> **Scope & honest expectations.** Matching a B200 / TPU v7 in *absolute*
> numbers (PFLOPS, 7.4 TB/s HBM) requires 3–5 nm silicon and is not reproducible
> in a single RTL project. MTU instead implements the same *architecture* in
> parameterizable RTL and demonstrates competitive **per-cycle throughput and
> efficiency** (utilization %, energy/op) in simulation and on FPGA. The array
> scales from a 16×16 FPGA build up to a 256×256 ASIC-class MXU (the TPU v6/v7
> MXU dimension) without RTL changes.

## Status

| Phase | Content | State |
|-------|---------|-------|
| 0 | Scaffolding, Verilator+cocotb flow, CI | ✅ done |
| 1 | INT8 Processing Element (MAC) + golden model | ✅ done |
| 2 | Parameterized NxN weight-stationary systolic MXU | ✅ done |
| 3 | Unified Buffer (double-buffered) + mini-ISA controller | ⏳ planned |
| 4 | Vector/Special-Function Unit + FP8/BF16 mixed precision | ⏳ planned |
| 5 | Top integration, AXI DMA, FPGA synth, benchmarks | ⏳ planned |

## Layout

```
rtl/        SystemVerilog sources
  pe/pe.sv                 single weight-stationary MAC
  mxu/systolic_array.sv    ROWS x COLS PE grid (parameterized)
  mtu_top.sv               top-level wrapper around the MXU
model/      numpy golden reference + dataflow skew helpers (golden.py)
tb/         cocotb testbenches + shared drivers
docs/       architecture.md, isa.md (Phase 3), benchmarks.md (Phase 5)
sim.py      build+run runner (Icarus Verilog)  ·  Makefile wraps it
```

## Quick start

```bash
pip install -r requirements.txt      # cocotb >= 2.0, numpy
sudo apt-get install -y iverilog verilator

make test     # build + run all cocotb testbenches
make lint     # Verilator lint of the full RTL
make systolic # run just the 4x4 systolic-array matmul tests
```

Every testbench drives real GEMMs through the RTL and compares the result
**bit-exactly** against the numpy golden model in `model/golden.py`.

See [`docs/architecture.md`](docs/architecture.md) for the dataflow, timing and
module-by-module design.
