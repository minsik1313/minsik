#!/usr/bin/env python3
"""Analog sizing-sweep automation (Phase 1 flow demo, plan §2.5).

Sweeps the transistor width W of a common-source amplifier, measures the
small-signal voltage gain in ngspice, and reports the smallest W that meets a
target gain. This is the skeleton of the ngspice-in-the-loop sizing loop; a
real flow swaps the constant sweep for MOBO / Bayesian optimisation and the
generic model for sky130 devices.

Requires: ngspice in PATH.
"""
import os
import re
import subprocess
import sys
import tempfile

DECK = """* CS amp sizing point (generic level-1 model)
Vdd   vdd 0 1.8
Vin   in  0 dc 0.7 ac 1
M1    out in 0 0 nch W={w}u L=1u
Rd    vdd out 10k
.model nch nmos (level=1 kp=120u vto=0.5 lambda=0.05)
.control
  ac dec 20 1 1G
  meas ac gain_db max vdb(out)
  print gain_db
.endc
.end
"""

TARGET_GAIN_DB = 20.0
W_SWEEP_UM = [2, 5, 10, 20, 50, 100]


def measure_gain(w_um: float):
    """Return small-signal gain (dB) for width w_um, or None if ngspice fails."""
    deck = DECK.format(w=w_um)
    with tempfile.NamedTemporaryFile("w", suffix=".spice", delete=False) as f:
        f.write(deck)
        path = f.name
    try:
        proc = subprocess.run(
            ["ngspice", "-b", path],
            capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    finally:
        os.unlink(path)
    m = re.search(r"gain_db\s*=\s*([-\d.eE+]+)", proc.stdout)
    return float(m.group(1)) if m else None


def main() -> int:
    print(f"Target gain >= {TARGET_GAIN_DB} dB\n")
    print(f"{'W (um)':>8} {'gain (dB)':>12}")
    print("-" * 22)
    best = None
    for w in W_SWEEP_UM:
        g = measure_gain(w)
        if g is None:
            print(f"{w:>8} {'ngspice N/A':>12}")
            continue
        print(f"{w:>8} {g:>12.2f}")
        if g >= TARGET_GAIN_DB and best is None:
            best = (w, g)
    print()
    if best:
        print(f"Smallest W meeting target: W={best[0]}um  (gain={best[1]:.2f} dB)")
        return 0
    print("No swept width met the target — widen the sweep or change topology.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
