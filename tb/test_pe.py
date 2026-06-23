"""Unit tests for a single Processing Element (rtl/pe/pe.sv)."""

import random

import cocotb
from cocotb.triggers import RisingEdge

from tb_utils import reset_dut, start_clock, to_signed


async def load_weight(dut, w):
    """Load a stationary weight via the load shift port."""
    dut.load_w.value = 1
    dut.w_in.value = w & 0xFF
    await RisingEdge(dut.clk)
    dut.load_w.value = 0
    dut.w_in.value = 0


@cocotb.test()
async def test_single_mac(dut):
    """psum_out should equal psum_in + a_in * w_reg, one cycle later."""
    await start_clock(dut)
    dut.load_w.value = 0
    dut.w_in.value = 0
    dut.a_in.value = 0
    dut.psum_in.value = 0
    await reset_dut(dut)

    await load_weight(dut, 7)

    # Drive a_in / psum_in, then check the registered MAC result next edge.
    dut.a_in.value = to_signed_byte(5)
    dut.psum_in.value = 100
    await RisingEdge(dut.clk)
    # Result is registered on this edge; sample after it settles.
    await RisingEdge(dut.clk)
    got = to_signed(int(dut.psum_out.value), 32)
    assert got == 100 + 5 * 7, f"expected {100 + 5*7}, got {got}"


@cocotb.test()
async def test_random_macs(dut):
    """Randomised signed MACs against a Python reference."""
    await start_clock(dut)
    dut.load_w.value = 0
    dut.w_in.value = 0
    dut.a_in.value = 0
    dut.psum_in.value = 0
    await reset_dut(dut)

    for _ in range(200):
        w = random.randint(-128, 127)
        a = random.randint(-128, 127)
        p = random.randint(-(1 << 20), (1 << 20))
        await load_weight(dut, w)
        dut.a_in.value = to_signed_byte(a)
        dut.psum_in.value = to_signed_byte32(p)
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        got = to_signed(int(dut.psum_out.value), 32)
        assert got == p + a * w, f"w={w} a={a} p={p}: expected {p + a*w}, got {got}"


@cocotb.test()
async def test_activation_passthrough(dut):
    """a_in should appear on a_out exactly one cycle later (systolic flow)."""
    await start_clock(dut)
    dut.load_w.value = 0
    dut.w_in.value = 0
    dut.a_in.value = 0
    dut.psum_in.value = 0
    await reset_dut(dut)

    seq = [3, -4, 17, -128, 127, 0]
    prev = None
    for val in seq:
        dut.a_in.value = to_signed_byte(val)
        await RisingEdge(dut.clk)
        if prev is not None:
            got = to_signed(int(dut.a_out.value), 8)
            assert got == prev, f"a_out expected {prev}, got {got}"
        prev = val


def to_signed_byte(v: int) -> int:
    return v & 0xFF


def to_signed_byte32(v: int) -> int:
    return v & 0xFFFFFFFF
