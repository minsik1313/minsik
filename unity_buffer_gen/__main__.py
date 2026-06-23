"""CLI entry point:  python -m unity_buffer_gen [options]

Automatically designs and verifies a sky130 unity-gain buffer for the given
spec, writes the netlists + report to an output directory.
"""

from __future__ import annotations

import argparse
import os
import sys

from .spec import BufferSpec
from .generator import design_buffer
from .pdk import find_pdk
from . import report
from . import simulate as sim


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unity_buffer_gen",
        description="Automatic sky130 unity-gain buffer (LDO follower) generator.",
    )
    p.add_argument("--vdd", type=float, default=1.2, help="supply/input voltage [V]")
    p.add_argument("--vout", type=float, default=0.8, help="output voltage [V]")
    p.add_argument("--vref", type=float, default=None, help="reference [V] (default=vout)")
    p.add_argument("--iload", type=float, default=10e-3, help="max load current [A]")
    p.add_argument("--cout", type=float, default=1e-6, help="output capacitor [F]")
    p.add_argument("--esr", type=float, default=0.0, help="output-cap ESR [ohm]")
    p.add_argument("--error-res", type=float, default=1.0,
                   help="target output resistance / load reg [ohm]")
    p.add_argument("--corner", default="tt", help="process corner (tt/ss/ff/sf/fs)")
    p.add_argument("--temp", type=float, default=27.0, help="temperature [C]")
    p.add_argument("--max-iter", type=int, default=8, help="max tuning iterations")
    p.add_argument("--outdir", default="output", help="artifact output directory")
    p.add_argument("--workdir", default=None, help="ngspice scratch dir")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not sim.ngspice_available():
        print("ERROR: ngspice not found on PATH.", file=sys.stderr)
        return 2
    try:
        pdk = find_pdk()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    spec = BufferSpec(
        vdd=args.vdd, vout=args.vout, vref=args.vref, iload_max=args.iload,
        cout=args.cout, cout_esr=args.esr, error_res=args.error_res,
        corner=args.corner, temp=args.temp,
    )
    workdir = args.workdir or os.path.join(args.outdir, "_work")
    if not args.quiet:
        print(f"PDK: {pdk.lib_path} ({pdk.variant})")
        print(f"Spec: VDD={spec.vdd} VOUT={spec.vout} Iload<= {spec.iload_max*1e3}mA "
              f"COUT={spec.cout*1e6}uF error_res={spec.error_res}ohm")

    res = design_buffer(spec, workdir=workdir, max_iter=args.max_iter,
                        pdk=pdk, verbose=not args.quiet)
    files = report.emit_artifacts(res, pdk, args.outdir)

    print("\n" + report.render_report(res, pdk))
    print(f"Artifacts written to: {os.path.abspath(args.outdir)}/")
    for name in sorted(files):
        print(f"  - {name}")
    return 0 if res.passed else 1


if __name__ == "__main__":
    sys.exit(main())
