"""Reusable driver that runs a full matmul through the systolic MXU.

Used by both test_systolic_array.py and test_mtu_top.py, which only differ in
the top-level module wrapping the same array. The driver mirrors the hardware
dataflow (weight load shift chain + diagonally skewed activations) and returns
the de-skewed result for bit-exact comparison against model/golden.py.
"""

from __future__ import annotations

import numpy as np
from cocotb.triggers import RisingEdge

from tb_utils import pack, reset_dut, start_clock, to_signed
from golden import deskew_outputs, skew_inputs, weight_load_seq


async def load_weights(dut, w: np.ndarray, data_w: int):
    """Shift the (ROWS x COLS) weight matrix into the array."""
    seq = weight_load_seq(w)            # one row-vector per cycle, length ROWS
    dut.load_w.value = 1
    dut.a_in.value = 0
    for frame in seq:
        dut.w_load_in.value = pack(frame, data_w)
        await RisingEdge(dut.clk)
    dut.load_w.value = 0
    dut.w_load_in.value = 0


async def run_matmul(dut, x: np.ndarray, w: np.ndarray,
                     rows: int, cols: int, data_w: int, acc_w: int) -> np.ndarray:
    """Drive Y = X @ W through the array and return the captured Y (M x COLS)."""
    m_dim, k_dim = x.shape
    assert k_dim == rows and w.shape == (rows, cols)

    await start_clock(dut)
    dut.load_w.value = 0
    dut.w_load_in.value = 0
    dut.a_in.value = 0
    await reset_dut(dut)

    await load_weights(dut, w, data_w)

    frames = skew_inputs(x, rows)               # X[m][k] enters row k at cycle m+k
    # Y[0][0] emerges at the bottom accumulator ROWS edges after the first
    # activation is driven (one MAC-register stage per array row, plus the
    # one-cycle drive-to-capture latency of the synchronous testbench).
    first_out_cycle = rows
    total_cycles = first_out_cycle + (m_dim - 1) + (cols - 1) + 2

    samples: list[list[int]] = []
    for e in range(total_cycles):
        frame = frames[e] if e < len(frames) else [0] * rows
        dut.a_in.value = pack(frame, data_w)
        await RisingEdge(dut.clk)
        raw = int(dut.y_out.value)
        mask = (1 << acc_w) - 1
        samples.append([to_signed((raw >> (n * acc_w)) & mask, acc_w)
                        for n in range(cols)])

    return deskew_outputs(samples, m_dim, rows, cols, first_out_cycle)
