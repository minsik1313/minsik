"""End-to-end matmul tests for the weight-stationary systolic MXU.

The DUT is built at 4x4 (see sim.py) so ROWS=COLS=4, DATA_W=8, ACC_W=32.
Every result is compared bit-exactly against the numpy golden model.
"""

import random

import cocotb
import numpy as np

from mxu_driver import run_matmul
from golden import matmul_int

ROWS, COLS, DATA_W, ACC_W = 4, 4, 8, 32


@cocotb.test()
async def test_identity_weight(dut):
    """Y = X @ I should reproduce X."""
    x = np.array([[1, 2, 3, 4],
                  [5, 6, 7, 8],
                  [-1, -2, -3, -4]], dtype=np.int64)
    w = np.eye(ROWS, COLS, dtype=np.int64)
    y = await run_matmul(dut, x, w, ROWS, COLS, DATA_W, ACC_W)
    exp = matmul_int(x, w)
    assert np.array_equal(y, exp), f"got\n{y}\nexpected\n{exp}"


@cocotb.test()
async def test_known_matmul(dut):
    """A small hand-checkable matmul."""
    x = np.array([[1, 2, 3, 4]], dtype=np.int64)
    w = np.array([[1, 0, 2, 0],
                  [0, 1, 0, 2],
                  [3, 0, 4, 0],
                  [0, 5, 0, 6]], dtype=np.int64)
    y = await run_matmul(dut, x, w, ROWS, COLS, DATA_W, ACC_W)
    exp = matmul_int(x, w)
    assert np.array_equal(y, exp), f"got\n{y}\nexpected\n{exp}"


@cocotb.test()
async def test_random_matmuls(dut):
    """Randomised signed INT8 matmuls of varying M."""
    for _ in range(25):
        m = random.randint(1, 6)
        x = np.random.randint(-128, 128, size=(m, ROWS), dtype=np.int64)
        w = np.random.randint(-128, 128, size=(ROWS, COLS), dtype=np.int64)
        y = await run_matmul(dut, x, w, ROWS, COLS, DATA_W, ACC_W)
        exp = matmul_int(x, w)
        assert np.array_equal(y, exp), f"x=\n{x}\nw=\n{w}\ngot\n{y}\nexpected\n{exp}"
