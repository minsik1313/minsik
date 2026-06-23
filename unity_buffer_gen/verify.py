"""Extended verification of a fixed buffer design: corners, line regulation,
quiescent current, and waveform capture (transient + AC loop gain).

Used to produce a verification report on top of the nominal (tt) design.
"""

from __future__ import annotations

import os
import re
import subprocess
from copy import copy

from .spec import BufferSpec, DeviceSizes, BiasPlan
from . import netlist as nl
from . import simulate as sim


def _settle_deck(pdk, spec, sz, bias, iload, vdd=None):
    """Power-up transient: ramp VDD and let the loop settle to the *stable*
    operating point (DC .op can latch onto the runaway root at slow corners /
    low VDD; transient power-up avoids it)."""
    vdd = spec.vdd if vdd is None else vdd
    return "\n".join([
        f'.lib "{pdk.lib_path}" {spec.corner}', ".option scale=1.0u",
        nl.buffer_subckt(sz),
        f"VDD VDD 0 PWL(0 0 20u {vdd:g} 400u {vdd:g})",
        f"VREF VREF 0 {spec.vref:g}",
        f"IREF VDD IBIAS {bias.iref:g}",
        "XBUF VDD 0 VREF VOUT IBIAS unity_buffer",
        f"COUT VOUT 0 {spec.cout:g}", f"ILOAD VOUT 0 {iload:g}",
        ".options gminsteps=20 sourcesteps=20",
        ".control", "tran 1u 400u",
        "let isup = -i(VDD)",
        "wrdata settle.txt v(VOUT) isup", ".endc", ".end",
    ])


def _run_op(pdk, spec, sz, bias, iload, workdir, vdd=None):
    deck = _settle_deck(pdk, spec, sz, bias, iload, vdd)
    path = sim.run_deck(deck, workdir, "settle.txt")
    rows = sim.read_columns(path)
    # use the tail of the transient (settled value)
    tail = rows[-50:] if len(rows) >= 50 else rows
    vout = sum(r[1] for r in tail) / len(tail)
    isup = sum((r[3] if len(r) >= 4 else r[2]) for r in tail) / len(tail)
    return vout, isup


def corners(pdk, spec, sz, bias, workdir,
            corner_list=("tt", "ss", "ff", "sf", "fs")):
    out = {}
    for c in corner_list:
        sp = copy(spec); sp.corner = c
        wd = os.path.join(workdir, f"corner_{c}")
        try:
            v_nl, i_nl = _run_op(pdk, sp, sz, bias, spec.iload_min, wd)
            v_fl, i_fl = _run_op(pdk, sp, sz, bias, spec.iload_max, wd)
            rout = abs(v_nl - v_fl) / (spec.iload_max - spec.iload_min)
            out[c] = {"vout_noload": v_nl, "vout_fullload": v_fl,
                      "rout_chord": rout, "iq_noload": i_nl - spec.iload_min,
                      "isup_fullload": i_fl}
        except Exception as e:
            out[c] = {"error": str(e)[:120]}
    return out


def line_reg(pdk, spec, sz, bias, workdir, iload=1e-3,
             vdd_lo=1.2, vdd_hi=1.3):
    wd = os.path.join(workdir, "linereg")
    v_lo, _ = _run_op(pdk, spec, sz, bias, iload, wd, vdd=vdd_lo)
    v_hi, _ = _run_op(pdk, spec, sz, bias, iload, wd, vdd=vdd_hi)
    return {"dvdd": vdd_hi - vdd_lo, "dvout": v_hi - v_lo,
            "line_reg_mv_per_v": (v_hi - v_lo) / (vdd_hi - vdd_lo) * 1e3,
            "vout_vdd_lo": v_lo, "vout_vdd_hi": v_hi}


def capture_ac(pdk, spec, sz, bias, workdir, iload):
    """Return (freq, gain_db, phase_deg) of the loop gain."""
    deck = nl.tb_ac_loop(pdk, spec, sz, bias, iload)
    path = sim.run_deck(deck, workdir, "ac_loop.txt")
    rows = sim.read_columns(path)
    f = [r[0] for r in rows]
    g = [r[1] for r in rows]
    p = [r[3] if len(r) >= 4 else r[2] for r in rows]
    return f, g, p


def capture_tran(pdk, spec, sz, bias, workdir):
    deck = nl.tb_tran_step(pdk, spec, sz, bias)
    path = sim.run_deck(deck, workdir, "tran_step.txt")
    t, v = sim.read_xy(path)
    return t, v
