"""Integration test for mtu_top: drives matmuls through the full top level.

Built at ARRAY_ROWS=ARRAY_COLS=8 (see sim.py) to exercise a larger array than
the unit-level systolic test and confirm the wrapper wires the MXU correctly.
"""

import random

import cocotb
import numpy as np

from mxu_driver import run_matmul
from golden import matmul_int

ROWS, COLS, DATA_W, ACC_W = 8, 8, 8, 32


@cocotb.test()
async def test_end_to_end_matmul(dut):
    """Random INT8 GEMMs through mtu_top, bit-exact vs numpy."""
    for _ in range(15):
        m = random.randint(1, 8)
        x = np.random.randint(-128, 128, size=(m, ROWS), dtype=np.int64)
        w = np.random.randint(-128, 128, size=(ROWS, COLS), dtype=np.int64)
        y = await run_matmul(dut, x, w, ROWS, COLS, DATA_W, ACC_W)
        exp = matmul_int(x, w)
        assert np.array_equal(y, exp), f"x=\n{x}\nw=\n{w}\ngot\n{y}\nexpected\n{exp}"
