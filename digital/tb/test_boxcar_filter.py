"""cocotb regression for boxcar_filter.

Reference model: a Python deque holding the last TAPS samples; the expected
output is the integer mean (sum >> LOG2_TAPS). This is the sign-off gate that
must stay green before any tapeout (see docs/FABLESS_PLAN.md §2.4).
"""
import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

DATA_WIDTH = 8
LOG2_TAPS = 3
TAPS = 1 << LOG2_TAPS


@cocotb.test()
async def test_moving_average(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.in_data.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    window = deque([0] * TAPS, maxlen=TAPS)
    random.seed(1)

    for i in range(256):
        sample = random.randint(0, (1 << DATA_WIDTH) - 1)
        dut.in_valid.value = 1
        dut.in_data.value = sample
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")  # let registered outputs settle past the edge

        window.append(sample)
        expected = sum(window) >> LOG2_TAPS

        assert dut.out_valid.value == 1, f"cycle {i}: out_valid not asserted"
        got = int(dut.out_data.value)
        assert got == expected, f"cycle {i}: got {got}, expected {expected}"

    # Deasserting valid must drop out_valid the next cycle.
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.out_valid.value == 0, "out_valid stuck high after in_valid low"
