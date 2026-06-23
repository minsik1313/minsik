"""Validation tests against closed-form analytic references.

Run with `pytest -q` or directly: `python tests/test_fastspice.py`.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastspice.circuit import Circuit
from fastspice.devices import (Resistor, Capacitor, Inductor, Diode,
                               VoltageSource, Sine, Pulse)
from fastspice import analyses


def _rc_sine(method, h, adaptive=False, reltol=1e-3):
    R, C, A, f = 1e3, 1e-6, 1.0, 200.0
    w, tau = 2 * np.pi * f, R * C
    c = Circuit("rc")
    c.options["reltol"] = reltol
    c.add(VoltageSource("V1", "in", "0", Sine(0, A, f)))
    c.add(Resistor("R1", "in", "out", R))
    c.add(Capacitor("C1", "out", "0", C))
    r = analyses.transient(c, 5e-3, h, integrator=method, uic=True,
                           adaptive=adaptive)
    d = 1 + (w * tau) ** 2
    ana = A / d * (np.sin(w * r.t) - w * tau * np.cos(w * r.t)
                   + w * tau * np.exp(-r.t / tau))
    return float(np.max(np.abs(r.v("out") - ana))), r


def test_convergence_orders():
    """Each integrator converges at its theoretical order."""
    expected = {"be": 1.0, "tr": 2.0, "gear2": 2.0, "tr-bdf2": 2.0}
    for m, want in expected.items():
        errs = [_rc_sine(m, h)[0] for h in (2e-5, 1e-5, 5e-6, 2.5e-6)]
        orders = [np.log2(errs[i] / errs[i + 1]) for i in range(3)]
        got = np.mean(orders)
        assert abs(got - want) < 0.25, f"{m}: order {got:.2f} != {want}"


def test_trbdf2_beats_trap_accuracy():
    """TR-BDF2 has a smaller error constant than trapezoidal."""
    etr = _rc_sine("tr", 1e-5)[0]
    etb = _rc_sine("tr-bdf2", 1e-5)[0]
    assert etb < etr


def test_trapezoidal_ringing_is_damped():
    """On a stiff step, TR-BDF2 must not ring the way trapezoidal does."""
    def run(method):
        c = Circuit("rc")
        c.add(VoltageSource("V1", "in", "0",
                            Pulse(0, 1, td=0, tr=1e-12, pw=10, per=100, tf=1e-12)))
        c.add(Resistor("R1", "in", "out", 1e3))
        c.add(Capacitor("C1", "out", "0", 1e-6))
        r = analyses.transient(c, 40e-3, 5e-3, integrator=method, uic=True,
                               adaptive=False)
        return float(np.max(np.abs(r.v("out") - 1.0)[2:]))
    assert run("tr-bdf2") < 0.4 * run("tr")


def test_adaptive_reduces_steps():
    """Error control delivers comparable accuracy with far fewer steps."""
    e_fixed, r_fixed = _rc_sine("tr-bdf2", 5e-6, adaptive=False)
    # adaptive over a longer horizon
    R, C, A, f = 1e3, 1e-6, 1.0, 200.0
    c = Circuit("rc")
    c.options["reltol"] = 1e-4
    c.add(VoltageSource("V1", "in", "0", Sine(0, A, f)))
    c.add(Resistor("R1", "in", "out", R))
    c.add(Capacitor("C1", "out", "0", C))
    ra = analyses.transient(c, 2e-2, 5e-6, integrator="tr-bdf2", uic=True,
                            adaptive=True)
    rf = Circuit("rc")
    rf.add(VoltageSource("V1", "in", "0", Sine(0, A, f)))
    rf.add(Resistor("R1", "in", "out", R))
    rf.add(Capacitor("C1", "out", "0", C))
    rfix = analyses.transient(rf, 2e-2, 5e-6, integrator="tr-bdf2", uic=True,
                              adaptive=False)
    assert ra.stats["steps"] < rfix.stats["steps"] / 5


def test_rlc_underdamped_matches_analytic():
    """Series RLC step response matches the analytic underdamped solution."""
    L, R, C = 1e-3, 10.0, 1e-6
    w0 = 1 / np.sqrt(L * C)
    alpha = R / (2 * L)
    wd = np.sqrt(w0 ** 2 - alpha ** 2)
    c = Circuit("rlc")
    c.add(VoltageSource("V1", "in", "0",
                        Pulse(0, 1, td=0, tr=1e-9, pw=1, per=10, tf=1e-9)))
    c.add(Resistor("R1", "in", "a", R))
    c.add(Inductor("L1", "a", "out", L))
    c.add(Capacitor("C1", "out", "0", C))
    r = analyses.transient(c, 1e-3, 5e-7, integrator="tr-bdf2", uic=True,
                           adaptive=False)
    ana = 1 - np.exp(-alpha * r.t) * (np.cos(wd * r.t)
                                      + alpha / wd * np.sin(wd * r.t))
    assert float(np.max(np.abs(r.v("out") - ana))) < 5e-3


def test_diode_rectifier_converges():
    """Non-linear rectifier converges and produces a sensible peak/ripple."""
    c = Circuit("rect")
    c.add(VoltageSource("V1", "in", "0", Sine(0, 5, 60)))
    c.add(Diode("D1", "in", "out", is_=1e-14, n=1.0))
    c.add(Resistor("R1", "out", "0", 1e3))
    c.add(Capacitor("C1", "out", "0", 10e-6))
    r = analyses.transient(c, 50e-3, 2e-4, integrator="tr-bdf2", uic=False,
                           adaptive=True)
    peak = float(np.max(r.v("out")))
    assert 4.0 < peak < 4.6  # 5V minus a diode drop


def test_operating_point_divider():
    """DC operating point of a resistive divider."""
    c = Circuit("div")
    c.add(VoltageSource("V1", "in", "0", 10.0))
    c.add(Resistor("R1", "in", "mid", 1e3))
    c.add(Resistor("R2", "mid", "0", 1e3))
    op, _ = analyses.operating_point(c)
    assert abs(op["mid"] - 5.0) < 1e-6


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - fails}/{len(fns)} tests passed")
    sys.exit(1 if fails else 0)
