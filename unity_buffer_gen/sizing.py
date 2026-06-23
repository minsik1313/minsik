"""Device characterization and geometry sanitization against the real PDK.

The sky130 ngspice models are *binned*; a few (L,W,nf) combinations land in
bins whose extracted parameters trip BSIM4's fatal checks (e.g. ``Dsub
negative``).  An automatic generator must not emit those.  `safe_geometry`
probes a candidate with a throw-away op simulation and, if it aborts, searches
nearby finger/length choices for one that simulates cleanly.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Tuple

from . import simulate as sim
from .pdk import Pdk


def _geometry_ok(pdk: Pdk, model: str, L: float, W: float, nf: int,
                 is_pmos: bool, workdir: str, corners=("tt",)) -> bool:
    """True if the geometry simulates cleanly in *every* requested corner.

    Some sky130 bins trip BSIM fatal checks only in certain corners (e.g. the
    pfet L=0.25 bin has Drout<0 at ss/sf).  Default is the tt probe; pass the
    full corner list to enforce corner-robust binning (note: that can force a
    much larger pass device, since the current-dense pfet bins are the ones
    with corner-specific model defects)."""
    corners = corners or ("tt",)
    if is_pmos:
        body = ["Vs s 0 1.2", "Vg g 0 0.4", "Vd d 0 0.6",
                f"XM d g s s {model} L={L} W={W} nf={nf} m=1"]
    else:
        body = ["Vd d 0 0.6", "Vg g 0 0.8",
                f"XM d g 0 0 {model} L={L} W={W} nf={nf} m=1"]
    wd = os.path.join(workdir, "_probe")
    for c in corners:
        deck = "\n".join([
            f'.lib "{pdk.lib_path}" {c}', ".option scale=1.0u", *body,
            ".control", "op", "wrdata probe.txt v(d)", ".endc", ".end",
        ])
        try:
            sim.run_deck(deck, wd, "probe.txt")
        except sim.NgspiceError:
            return False
    return True


_L_LADDER = [0.15, 0.18, 0.25, 0.3, 0.35, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0,
             3.0, 4.0, 6.0, 8.0]


def safe_geometry(pdk: Pdk, model: str, L: float, W: float, nf: int,
                  workdir: str) -> Tuple[float, float, int]:
    """Return a (L,W,nf) close to the request that simulates cleanly.

    Tries the request, then alternate finger counts, then snaps L to a ladder
    value at/above the request.  Raises if nothing works.
    """
    is_pmos = "pfet" in model
    candidates = [(L, W, nf)]
    # prefer keeping the finger count and lengthening (preserves current
    # density / drive); only then fall back to changing nf.  Dropping nf at a
    # fixed L can find a clean-but-tiny bin and explode the multiplier.
    for Lsnap in _L_LADDER:
        if Lsnap >= L - 1e-9:
            candidates.append((Lsnap, W, nf))
    for nf_try in (1, 2, 4):
        if nf_try != nf:
            candidates.append((L, W, nf_try))
    for Lsnap in _L_LADDER:
        if Lsnap >= L - 1e-9:
            for nf_try in (1, 2, 4):
                if nf_try != nf:
                    candidates.append((Lsnap, W, nf_try))
    seen = set()
    for cand in candidates:
        key = (round(cand[0], 4), round(cand[1], 4), cand[2])
        if key in seen:
            continue
        seen.add(key)
        if _geometry_ok(pdk, model, cand[0], cand[1], cand[2], is_pmos,
                        workdir):
            return cand
    raise RuntimeError(f"no clean geometry near {model} L={L} W={W} nf={nf}")


def pass_cell_current(pdk: Pdk, spec, sz, workdir: str,
                      gate: float = 0.2) -> float:
    """|Id| of one pass cell at the given gate voltage (Vsd = vdd-vout)."""
    from . import netlist as nl
    deck = nl.tb_char_pass(pdk, spec, sz)
    path = sim.run_deck(deck, workdir, "char_pass.txt")
    x, y = sim.read_xy(path)  # x=gate, y=id (signed)
    best = None
    for g, idv in zip(x, y):
        if best is None or abs(g - gate) < abs(best[0] - gate):
            best = (g, idv)
    return max(abs(best[1]), 1e-12) if best else 1e-12
