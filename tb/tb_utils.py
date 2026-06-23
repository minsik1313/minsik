"""Shared helpers for the MTU cocotb testbenches.

Handles two's-complement packing/unpacking of the flattened vector ports used
by the RTL (see rtl/mxu/systolic_array.sv for the bit layout).
"""

from __future__ import annotations

from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


def to_unsigned(value: int, width: int) -> int:
    """Two's-complement encode a (possibly negative) integer into `width` bits."""
    return value & ((1 << width) - 1)


def to_signed(value: int, width: int) -> int:
    """Interpret the low `width` bits of `value` as a signed two's-complement int."""
    value &= (1 << width) - 1
    if value & (1 << (width - 1)):
        value -= 1 << width
    return value


def pack(values, width: int) -> int:
    """Pack a list of signed ints into one integer, element 0 in the low bits."""
    packed = 0
    for i, v in enumerate(values):
        packed |= to_unsigned(v, width) << (i * width)
    return packed


def unpack(packed: int, count: int, width: int) -> list[int]:
    """Inverse of `pack`: extract `count` signed ints of `width` bits each."""
    mask = (1 << width) - 1
    return [to_signed((packed >> (i * width)) & mask, width) for i in range(count)]


async def start_clock(dut, period_ns: int = 10):
    """Launch a free-running clock on dut.clk."""
    import cocotb
    cocotb.start_soon(Clock(dut.clk, period_ns, unit="ns").start())


async def reset_dut(dut, cycles: int = 2):
    """Assert active-low reset for `cycles` clocks, then release."""
    dut.rst_n.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
