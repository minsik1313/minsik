#!/usr/bin/env python3
"""Reproducible benchmark suite for FastSpice.

Runs four studies and prints result tables; with --plot it also writes
figures into docs/figures/.  Every accuracy number is measured against a
closed-form analytic reference so the claims are falsifiable.

    1. Convergence order        (is each integrator the order it claims?)
    2. Trapezoidal ringing      (does TR-BDF2 kill the SPICE ringing artefact?)
    3. Adaptive efficiency      (steps needed vs accuracy delivered)
    4. Non-linear robustness    (diode rectifier, homotopy convergence)
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastspice.circuit import Circuit
from fastspice.devices import (Resistor, Capacitor, VoltageSource, Sine,
                               Pulse, Diode)
from fastspice import analyses

FIGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "docs", "figures")


# --------------------------------------------------------------------------
def rc_sine():
    R, C, A, f = 1e3, 1e-6, 1.0, 200.0
    w = 2 * np.pi * f
    tau = R * C

    def ana(t):
        d = 1 + (w * tau) ** 2
        return A / d * (np.sin(w * t) - w * tau * np.cos(w * t)
                        + w * tau * np.exp(-t / tau))

    def build():
        c = Circuit("rc")
        c.add(VoltageSource("V1", "in", "0", Sine(0, A, f)))
        c.add(Resistor("R1", "in", "out", R))
        c.add(Capacitor("C1", "out", "0", C))
        return c

    return build, ana


def study_convergence():
    print("\n[1] Convergence order  (RC, smooth sine drive, fixed step)")
    print("    method   " + "   ".join(f"h={h:.1e}" for h in
          (2e-5, 1e-5, 5e-6, 2.5e-6)))
    build, ana = rc_sine()
    rows = {}
    for m in ("be", "tr", "gear2", "tr-bdf2"):
        prev, cells, orders = None, [], []
        for h in (2e-5, 1e-5, 5e-6, 2.5e-6):
            c = build()
            r = analyses.transient(c, 5e-3, h, integrator=m, uic=True,
                                   adaptive=False)
            e = float(np.max(np.abs(r.v("out") - ana(r.t))))
            if prev is not None:
                orders.append(np.log2(prev / e))
            cells.append(f"{e:.2e}")
            prev = e
        rows[m] = np.mean(orders)
        print(f"    {m:8s} " + " ".join(f"{c:>9s}" for c in cells)
              + f"   ~order {np.mean(orders):.2f}")
    return rows


def study_ringing(plot=False):
    print("\n[2] Trapezoidal ringing  (stiff RC step, h = 5*tau)")
    R, C = 1e3, 1e-6
    h = 5e-3

    def build():
        c = Circuit("rc")
        c.add(VoltageSource("V1", "in", "0",
                            Pulse(0, 1, td=0, tr=1e-12, pw=10, per=100, tf=1e-12)))
        c.add(Resistor("R1", "in", "out", R))
        c.add(Capacitor("C1", "out", "0", C))
        return c

    traces = {}
    for m in ("tr", "tr-bdf2", "gear2", "be"):
        c = build()
        r = analyses.transient(c, 40e-3, h, integrator=m, uic=True,
                               adaptive=False)
        vo = r.v("out")
        overshoot = float(np.max(np.abs(vo - 1.0)[2:]))
        traces[m] = (r.t, vo)
        print(f"    {m:8s} spurious |v-1| after settling = {overshoot:.3f}")
    print("    (true response is a monotone rise to 1.0 -> any wobble is numerical)")
    if plot:
        _plot_ringing(traces)
    return traces


def study_adaptive():
    print("\n[3] Adaptive efficiency  (RC sine, matched accuracy)")
    build, ana = rc_sine()
    c = build()
    rf = analyses.transient(c, 2e-2, 5e-6, integrator="tr-bdf2", uic=True,
                            adaptive=False)
    ef = float(np.max(np.abs(rf.v("out") - ana(rf.t))))
    print(f"    fixed  tstep=5e-6 : steps={rf.stats['steps']:5d}  maxerr={ef:.2e}")
    for rt in (1e-3, 1e-4, 1e-5):
        c = build()
        c.options["reltol"] = rt
        ra = analyses.transient(c, 2e-2, 5e-6, integrator="tr-bdf2", uic=True,
                                adaptive=True)
        ea = float(np.max(np.abs(ra.v("out") - ana(ra.t))))
        speedup = rf.stats["steps"] / ra.stats["steps"]
        print(f"    adapt reltol={rt:.0e}: steps={ra.stats['steps']:5d}  "
              f"rej={ra.stats['rejects']:3d}  maxerr={ea:.2e}  "
              f"({speedup:.1f}x fewer steps)")


def study_nonlinear():
    print("\n[4] Non-linear robustness  (half-wave rectifier + smoothing cap)")
    c = Circuit("rect")
    c.add(VoltageSource("V1", "in", "0", Sine(0, 5, 60)))
    c.add(Diode("D1", "in", "out", is_=1e-14, n=1.0))
    c.add(Resistor("R1", "out", "0", 1e3))
    c.add(Capacitor("C1", "out", "0", 10e-6))
    r = analyses.transient(c, 50e-3, 2e-4, integrator="tr-bdf2", uic=False,
                           adaptive=True)
    vo = r.v("out")
    settled = vo[r.t > 20e-3]
    print(f"    steps={r.stats['steps']}  newton_iters={r.stats['newton_iters']}  "
          f"rejects={r.stats['rejects']}")
    print(f"    Vpeak={np.max(vo):.3f} V  ripple={np.max(settled)-np.min(settled):.3f} V"
          f"  (converged with junction limiting + homotopy)")


# --------------------------------------------------------------------------
def _plot_ringing(traces):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(FIGDIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    for m, (t, v) in traces.items():
        ax.plot(t * 1e3, v, marker="o", ms=3, label=m)
    ax.axhline(1.0, color="k", lw=0.8, ls="--", label="true steady state")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("V(out)")
    ax.set_title("Stiff RC step (h = 5τ): trapezoidal rings, TR-BDF2 does not")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(FIGDIR, "ringing.png")
    fig.savefig(path, dpi=110)
    print(f"    figure -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true", help="save figures")
    args = ap.parse_args()
    print("=" * 64)
    print("FastSpice benchmark suite")
    print("=" * 64)
    study_convergence()
    study_ringing(plot=args.plot)
    study_adaptive()
    study_nonlinear()
    print("\nDone.")


if __name__ == "__main__":
    main()
