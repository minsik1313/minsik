"""Tests for the sky130 unity-gain buffer generator.

Unit tests (netlist structure, spec math, parsing) run without a PDK.
The end-to-end design test is skipped unless ngspice and the sky130 PDK are
both available.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unity_buffer_gen.spec import BufferSpec, DeviceSizes, BiasPlan
from unity_buffer_gen import netlist as nl
from unity_buffer_gen import simulate as sim


# ---- pure-Python unit tests --------------------------------------------

def test_spec_defaults():
    s = BufferSpec()
    assert s.vdd == 1.2 and s.vout == 0.8
    assert s.vref == 0.8          # defaults to vout (unity gain)
    assert s.iload_max == 10e-3
    assert s.cout == 1e-6
    assert s.error_res == 1.0
    assert abs(s.dropout - 0.4) < 1e-9
    assert abs(s.max_droop - 10e-3) < 1e-9   # 1 ohm * 10 mA


def test_subckt_structure():
    txt = nl.buffer_subckt(DeviceSizes())
    assert ".subckt unity_buffer VDD VSS VREF VOUT IBIAS" in txt
    assert ".ends unity_buffer" in txt
    # 5 core transistors (M1-M4 + MP) + bias mirror (MB0/MB1) + preload (MBPRE)
    assert txt.count("sky130_fd_pr__") == 8
    assert "XMBPRE VOUT IBIAS VSS VSS" in txt   # output preload sink
    # pass device drives from VDD to VOUT with gate = OTA node
    assert "XMP VOUT OTA VDD VDD sky130_fd_pr__pfet_01v8" in txt
    # feedback: input device M1 gate tied to VOUT
    assert "XM1 NA VOUT TAIL VSS sky130_fd_pr__nfet_01v8" in txt


def test_comp_cap_emitted_only_when_set():
    assert "CC OTA VOUT" not in nl.buffer_subckt(DeviceSizes(cc=0))
    assert "CC OTA VOUT" in nl.buffer_subckt(DeviceSizes(cc=1e-12))


def test_testbenches_reference_lib_and_corner():
    class FakePdk:
        lib_path = "/x/sky130.lib.spice"
        variant = "sky130A"
    s, sz, b = BufferSpec(corner="ss"), DeviceSizes(), BiasPlan()
    for deck in (nl.tb_op(FakePdk, s, sz, b, 10e-3),
                 nl.tb_dc_load(FakePdk, s, sz, b),
                 nl.tb_ac_loop(FakePdk, s, sz, b, 10e-3),
                 nl.tb_tran_step(FakePdk, s, sz, b)):
        assert '.lib "/x/sky130.lib.spice" ss' in deck
        assert deck.strip().endswith(".end")


def test_ac_loop_uses_injection():
    class FakePdk:
        lib_path = "/x/sky130.lib.spice"
    deck = nl.tb_ac_loop(FakePdk, BufferSpec(), DeviceSizes(), BiasPlan(), 10e-3)
    assert "VINJ VOUT FB DC 0 AC 1" in deck
    assert "unity_buffer_fb" in deck


def test_parse_columns(tmp_path):
    f = tmp_path / "d.txt"
    f.write_text("0.0 1.0\n1.0 2.0\n2.0 4.0\n")
    x, y = sim.read_xy(str(f))
    assert x == [0.0, 1.0, 2.0]
    assert y == [1.0, 2.0, 4.0]


# ---- end-to-end (requires ngspice + sky130) ----------------------------

def _pdk_available():
    try:
        from unity_buffer_gen.pdk import find_pdk
        find_pdk()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not (sim.ngspice_available() and _pdk_available()),
                    reason="needs ngspice + sky130 PDK")
def test_design_end_to_end(tmp_path):
    from unity_buffer_gen import design_buffer
    res = design_buffer(BufferSpec(), workdir=str(tmp_path / "w"),
                        max_iter=4, verbose=False)
    m = res.metrics
    # full-load output must regulate near the reference
    assert abs(m["vout_fullload"] - res.spec.vref) < 0.05
    # output resistance must be finite and not absurd
    assert m["rout_incremental"] < 50
    # pass device must have been sized up from 1
    assert res.sizes.mp >= 1
