#!/usr/bin/env python3
"""autosize.py — Voltage-domain-aware analog sizing/structure automation.

Pipeline (plan §2.5, addressing "전압 domain에 따른 소자/사이징/구조 선정"):

    spec(Vdd, gain) ─▶ select voltage DOMAIN ─▶ pin sky130 device flavor
                    ─▶ set bias from Vth+Vov ─▶ for each TOPOLOGY (CS→2-stage):
                          sweep W in ngspice, keep points that
                            (a) meet the gain target, AND
                            (b) keep the device in saturation w/ headroom, AND
                            (c) respect the device Vds rating
                       ─▶ first topology with a valid sizing wins.

This is a principled skeleton, not a production synthesizer: the constant
W-sweep stands in for gm/Id + MOBO, and the Level-1 demo models stand in for
sky130. Both swap cleanly (see analog/README.md). Requires: ngspice in PATH.
"""
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from tech import select_domain, VoltageDomain          # noqa: E402
from topology import TOPOLOGIES                          # noqa: E402

W_SWEEP_UM = [2, 5, 10, 20, 30, 50, 75, 100]
HEADROOM = 0.05  # V margin kept away from the saturation edge and the rail


@dataclass
class SizingResult:
    spec_name: str
    domain: VoltageDomain
    topology: str
    w_um: float
    gain_db: float
    vout_dc: float
    ok: bool
    reason: str = ""


def _run_ngspice(deck: str):
    """Return (gain_db, vout_dc) parsed from an ngspice batch run, or (None, None)."""
    with tempfile.NamedTemporaryFile("w", suffix=".spice", delete=False) as f:
        f.write(deck)
        path = f.name
    try:
        proc = subprocess.run(
            ["ngspice", "-b", path], capture_output=True, text=True, timeout=60
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, None
    finally:
        os.unlink(path)
    out = proc.stdout
    g = re.search(r"gain_db\s*=\s*([-\d.eE+]+)", out)
    v = re.search(r"vout_dc\s*=\s*([-\d.eE+]+)", out)
    return (float(g.group(1)) if g else None,
            float(v.group(1)) if v else None)


def size_circuit(name: str, vdd: float, gain_target_db: float) -> SizingResult:
    dom = select_domain(vdd)                 # ── device-flavor selection
    vbias = dom.vth_n + dom.vov              # ── domain-aware biasing
    # Saturation/headroom window for the output node.
    v_lo, v_hi = dom.vov + HEADROOM, vdd - HEADROOM

    best = None
    for topo_name, gen in TOPOLOGIES:        # ── structure selection (CS → 2-stage)
        for w in W_SWEEP_UM:
            gain, vout = _run_ngspice(gen(dom, w, vbias))
            if gain is None or vout is None:
                continue
            in_window = v_lo <= vout <= v_hi
            vds_ok = vout <= dom.vds_max     # ── voltage-domain safety
            if gain >= gain_target_db and in_window and vds_ok:
                return SizingResult(name, dom, topo_name, w, gain, vout, True,
                                    "meets gain within headroom & Vds rating")
            # remember the closest valid-bias attempt for diagnostics
            if in_window and vds_ok and (best is None or gain > best.gain_db):
                best = SizingResult(name, dom, topo_name, w, gain, vout, False,
                                    "best biased point, gain below target")
    if best:
        return best
    return SizingResult(name, dom, "n/a", 0, float("nan"), float("nan"),
                        False, "no sizing kept the device biased in saturation")


def _report(r: SizingResult) -> None:
    status = "OK " if r.ok else "MISS"
    print(f"[{status}] {r.spec_name}")
    print(f"   domain   : {r.domain.name}  (Vdd_nom={r.domain.vdd_nom} V, "
          f"Vds_max={r.domain.vds_max} V)")
    print(f"   device   : {r.domain.nfet}")
    print(f"   topology : {r.topology}")
    if r.ok or r.topology != "n/a":
        print(f"   sizing   : W={r.w_um} um, L=1 um")
        print(f"   gain     : {r.gain_db:.2f} dB   Vout_dc={r.vout_dc:.3f} V")
    print(f"   note     : {r.reason}\n")


# Demo specs spanning two voltage domains + a structure-driving high-gain case.
DEMO_SPECS = [
    ("low-V sensor preamp", 1.8, 18.0),
    ("high-gain stage @1.8V", 1.8, 30.0),   # forces escalation to two_stage
    ("5V actuator driver", 5.0, 16.0),      # forces thick-oxide device flavor
]


def main() -> int:
    print("=== Voltage-domain-aware analog autosizer ===\n")
    rc = 0
    for name, vdd, gain in DEMO_SPECS:
        r = size_circuit(name, vdd, gain)
        _report(r)
        rc |= 0 if r.ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
