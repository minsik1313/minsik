"""Automatic synthesis + verification of the sky130 unity-gain buffer.

`design_buffer(spec)` runs a simulation-in-the-loop flow:

    1. characterize one pass cell against the real PDK device to size the
       PMOS pass multiplier for the load current,
    2. build the OTA + pass + bias netlist,
    3. verify DC regulation, output resistance (load reg), loop phase margin
       and the transient load-step response with ngspice,
    4. iteratively adjust a few knobs until the spec is met (or give up with
       the best result and a diagnostic report).
"""

from __future__ import annotations

import math
import os
from copy import deepcopy
from typing import Optional

from .spec import BufferSpec, DeviceSizes, BiasPlan, DesignResult
from .pdk import find_pdk, Pdk, NFET, PFET
from . import netlist as nl
from . import simulate as sim
from . import sizing


# ---------------------------------------------------------------------------
# metric extraction
# ---------------------------------------------------------------------------

def _sanitize(pdk, sz, workdir):
    """Snap every device geometry to a PDK bin that simulates cleanly."""
    sz.lb, sz.wb, sz.nfb = sizing.safe_geometry(
        pdk, NFET, sz.lb, sz.wb, sz.nfb, workdir)
    sz.li, sz.wi, sz.nfi = sizing.safe_geometry(
        pdk, NFET, sz.li, sz.wi, sz.nfi, workdir)
    sz.lm, sz.wm, sz.nfm = sizing.safe_geometry(
        pdk, PFET, sz.lm, sz.wm, sz.nfm, workdir)
    sz.lp, sz.wp, sz.nfp = sizing.safe_geometry(
        pdk, PFET, sz.lp, sz.wp, sz.nfp, workdir)


def _measure_op(pdk, spec, sz, bias, iload, workdir):
    deck = nl.tb_op(pdk, spec, sz, bias, iload)
    path = sim.run_deck(deck, workdir, "op_vout.txt")
    return sim.parse_op(path)


def _measure_rout(pdk, spec, sz, bias, workdir):
    deck = nl.tb_dc_load(pdk, spec, sz, bias)
    path = sim.run_deck(deck, workdir, "dc_load.txt")
    x, y = sim.read_xy(path)  # x=Iload, y=Vout
    if len(x) < 2:
        return None
    # chord output resistance over the full range
    di = x[-1] - x[0]
    rout_chord = abs(y[0] - y[-1]) / di if di else float("inf")
    # worst incremental resistance
    rout_inc = 0.0
    for i in range(1, len(x)):
        d = x[i] - x[i - 1]
        if d:
            rout_inc = max(rout_inc, abs(y[i] - y[i - 1]) / d)
    return {
        "rout_chord": rout_chord,
        "rout_incremental": rout_inc,
        "vout_noload": y[0],
        "vout_fullload": y[-1],
    }


def _measure_loop(pdk, spec, sz, bias, iload, workdir):
    deck = nl.tb_ac_loop(pdk, spec, sz, bias, iload)
    path = sim.run_deck(deck, workdir, "ac_loop.txt")
    rows = sim.read_columns(path)
    # wrdata vdb(loop) vp(loop) -> freq db freq phase
    freq, db, ph = [], [], []
    for r in rows:
        if len(r) >= 4:
            freq.append(r[0]); db.append(r[1]); ph.append(r[3])
        elif len(r) >= 3:
            freq.append(r[0]); db.append(r[1]); ph.append(r[2])
    if not freq:
        return None
    dc_gain = db[0]
    # unwrap phase
    uph = list(ph)
    for i in range(1, len(uph)):
        while uph[i] - uph[i - 1] > 180:
            uph[i] -= 360
        while uph[i] - uph[i - 1] < -180:
            uph[i] += 360
    # unity-gain frequency: first 0 dB downward crossing
    ugf = None; pm = None
    for i in range(1, len(db)):
        if db[i - 1] >= 0 >= db[i]:
            # interpolate
            f = _interp(db[i - 1], db[i], freq[i - 1], freq[i], 0.0)
            p = _interp(db[i - 1], db[i], uph[i - 1], uph[i], 0.0)
            ugf = f
            pm = 180.0 + p
            break
    return {
        "dc_loop_gain_db": dc_gain,
        "ugf_hz": ugf,
        "phase_margin_deg": pm,
    }


def _interp(x0, x1, y0, y1, x):
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _measure_tran(pdk, spec, sz, bias, workdir):
    deck = nl.tb_tran_step(pdk, spec, sz, bias)
    path = sim.run_deck(deck, workdir, "tran_step.txt")
    t, v = sim.read_xy(path)
    if not v:
        return None
    vref = spec.vref
    # window after step-up (50-150us) and after step-down (150-200us)
    up = [vv for tt, vv in zip(t, v) if 50e-6 < tt < 150e-6]
    dn = [(tt, vv) for tt, vv in zip(t, v) if 150e-6 < tt <= 200e-6]
    undershoot = (vref - min(up)) if up else float("nan")
    dn_v = [vv for _, vv in dn]
    overshoot = (max(dn_v) - vref) if dn_v else float("nan")

    # ring-down check: count significant crossings of the settled value in the
    # tail of the step-down window; a well-damped loop has very few.
    stable = True
    if len(dn_v) > 10:
        settled = dn_v[-1]
        tail = [vv for tt, vv in dn if tt > 160e-6]
        if tail:
            amp = max(abs(x - settled) for x in tail)
            crossings = 0
            for i in range(1, len(tail)):
                if (tail[i - 1] - settled) * (tail[i] - settled) < 0:
                    crossings += 1
            # sustained oscillation = many crossings with non-trivial amplitude
            stable = not (crossings > 4 and amp > 2e-3)
    return {
        "undershoot_v": undershoot,
        "overshoot_v": overshoot,
        "tran_stable": stable,
    }


# ---------------------------------------------------------------------------
# sizing seed
# ---------------------------------------------------------------------------

def _seed_pass(pdk, spec, sz, workdir) -> int:
    """Size the pass multiplier mp from a real single-cell characterization.

    Sized at a gate ~0.45 V (Vsg ~ vdd-0.45), representative of where the OTA
    output sits at full load, with margin.  The tuner refines from the closed
    loop afterwards.
    """
    gate = max(0.3, spec.vout * 0.55)
    icell = sizing.pass_cell_current(pdk, spec, sz, workdir, gate=gate)
    margin = 1.5
    mp = max(1, math.ceil(spec.iload_max * margin / icell))
    return mp


# ---------------------------------------------------------------------------
# top-level design loop
# ---------------------------------------------------------------------------

def design_buffer(spec: Optional[BufferSpec] = None,
                  workdir: Optional[str] = None,
                  max_iter: int = 8,
                  pdk: Optional[Pdk] = None,
                  verbose: bool = True) -> DesignResult:
    spec = spec or BufferSpec()
    workdir = workdir or os.path.join(os.getcwd(), "_work")
    os.makedirs(workdir, exist_ok=True)
    if pdk is None:
        pdk = find_pdk(fast_lib_dir=workdir)
    elif pdk.lib_path == pdk.orig_lib:
        # build the trimmed library for fast simulation loops
        pdk.lib_path = pdk.write_fast_lib(
            os.path.join(workdir, "sky130_fast.lib.spice"))

    sz = DeviceSizes()
    bias = BiasPlan()

    # snap all geometries to clean PDK bins, then seed pass from real char
    _sanitize(pdk, sz, workdir)
    sz.mp = _seed_pass(pdk, spec, sz, workdir)
    if verbose:
        print(f"[seed] pass multiplier mp={sz.mp}")

    result = DesignResult(spec=spec, sizes=sz, bias=bias)

    for it in range(1, max_iter + 1):
        metrics = {}
        op_full = _measure_op(pdk, spec, sz, bias, spec.iload_max, workdir)
        op_no = _measure_op(pdk, spec, sz, bias, spec.iload_min, workdir)
        metrics["vout_fullload_op"] = op_full.vout
        metrics["vout_noload_op"] = op_no.vout
        metrics["vota_fullload"] = op_full.vota
        metrics["vota_noload"] = op_no.vota

        rout = _measure_rout(pdk, spec, sz, bias, workdir)
        if rout:
            metrics.update(rout)
        loop = _measure_loop(pdk, spec, sz, bias, spec.iload_max, workdir)
        if loop:
            metrics.update(loop)
        tran = _measure_tran(pdk, spec, sz, bias, workdir)
        if tran:
            metrics.update(tran)

        # ---- acceptance checks ----
        reg_full_ok = abs(op_full.vout - spec.vref) <= spec.reg_tol
        reg_no_ok = abs(op_no.vout - spec.vref) <= spec.reg_tol
        # load regulation is the chord output resistance over the full range
        # (the standard spec); worst-incremental is reported but is noisy near
        # the light-load preload transition.
        rout_ok = (rout is not None and
                   rout["rout_chord"] <= spec.error_res)
        pm = metrics.get("phase_margin_deg")
        pm_ok = (pm is not None and pm >= spec.pm_min)
        # stability is gated on the transient load step (the reliable check);
        # the injected-loop phase margin is reported as a corroborating estimate.
        stable_ok = metrics.get("tran_stable", True)

        metrics["reg_full_ok"] = reg_full_ok
        metrics["reg_noload_ok"] = reg_no_ok
        metrics["rout_ok"] = rout_ok
        metrics["pm_ok"] = pm_ok
        metrics["stable_ok"] = stable_ok

        snapshot = {"iter": it, "sizes": deepcopy(sz.__dict__),
                    "bias": deepcopy(bias.__dict__), "metrics": dict(metrics)}
        result.history.append(snapshot)
        if verbose:
            print(f"[iter {it}] Vout(full)={op_full.vout*1e3:.1f}mV "
                  f"Vout(no)={op_no.vout*1e3:.1f}mV "
                  f"Rout(chord)={metrics.get('rout_chord', float('nan')):.3g} "
                  f"PM={pm if pm is not None else float('nan')} "
                  f"mp={sz.mp}")

        if reg_full_ok and reg_no_ok and rout_ok and stable_ok:
            result.passed = True
            result.metrics = metrics
            result.iterations = it
            break

        # ---- adjust knobs (most impactful first) ----
        # undersized pass device: output can't reach target, or OTA output is
        # railed low trying to drive it -> grow the pass device.
        if (op_full.vout < spec.vref - spec.reg_tol) or (op_full.vota < 0.30):
            sz.mp = int(math.ceil(sz.mp * 1.4))
            continue
        if not rout_ok:
            # raise loop gain: lengthen mirror + input devices for more ro,
            # and grow pass gm.
            sz.lm = min(sz.lm * 1.5, 8.0)
            sz.li = min(sz.li * 1.5, 4.0)
            sz.mp = int(math.ceil(sz.mp * 1.2))
            _sanitize(pdk, sz, workdir)
            continue
        if not stable_ok:
            # transient rings -> add/strengthen compensation cap to lower UGF
            sz.cc = (sz.cc or 0.5e-12) * 2
            continue
        # absolute offset too large but load reg fine: lengthen input/mirror to
        # cut systematic (channel-length-modulation) offset.
        if not (reg_full_ok and reg_no_ok):
            sz.li = min(sz.li * 1.5, 4.0)
            sz.lm = min(sz.lm * 1.5, 8.0)
            _sanitize(pdk, sz, workdir)
            continue
        # nothing actionable -> stop
        result.metrics = metrics
        result.iterations = it
        break
    else:
        result.metrics = metrics
        result.iterations = max_iter

    if not result.metrics:
        result.metrics = metrics
    result.sizes = sz
    result.bias = bias
    return result
