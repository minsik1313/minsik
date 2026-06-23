"""Command-line runner:  python -m fastspice circuit.cir [options]

Parses a netlist, runs its .tran card (or DC operating point if none), and
prints the requested node waveforms / op-point.  Use --csv to dump the full
waveform table.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from .parser import parse_file
from . import analyses


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fastspice")
    ap.add_argument("netlist")
    ap.add_argument("--method", default="tr-bdf2",
                    help="be | tr | gear2 | tr-bdf2 (default)")
    ap.add_argument("--no-adaptive", action="store_true")
    ap.add_argument("--print", dest="nodes", default="",
                    help="comma-separated node names to print")
    ap.add_argument("--csv", default=None, help="write full waveform CSV here")
    args = ap.parse_args(argv)

    circuit, tran = parse_file(args.netlist)

    op, _ = analyses.operating_point(circuit)
    print("# operating point")
    for name, v in sorted(op.items()):
        print(f"  V({name}) = {v: .6g}")

    if tran is None:
        return 0

    res = analyses.transient(circuit, tran["tstop"], tran["tstep"],
                             integrator=args.method, tstart=tran["tstart"],
                             uic=tran["uic"], adaptive=not args.no_adaptive)
    print(f"\n# transient ({res.stats['method']}): {res.stats}")

    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()] \
        or sorted(op.keys())
    if args.csv:
        cols = ["t"] + nodes
        data = np.column_stack([res.t] + [res.v(n) for n in nodes])
        np.savetxt(args.csv, data, delimiter=",", header=",".join(cols),
                   comments="")
        print(f"# wrote {len(res.t)} rows -> {args.csv}")
    else:
        idx = np.linspace(0, len(res.t) - 1, min(11, len(res.t))).astype(int)
        print("  t        " + "  ".join(f"V({n})" for n in nodes))
        for i in idx:
            print(f"  {res.t[i]:.4e} " +
                  "  ".join(f"{res.v(n)[i]: .4f}" for n in nodes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
