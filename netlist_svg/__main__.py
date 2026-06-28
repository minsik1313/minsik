"""CLI: python -m netlist_svg <netlist.sp> [-o out.svg]"""

from __future__ import annotations

import argparse
import os
import sys

from . import parse_file, place, render


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert a SPICE MOSFET netlist to an SVG schematic.")
    ap.add_argument("netlist", help="input SPICE netlist (.sp/.cir)")
    ap.add_argument("-o", "--out", help="output SVG path (default: <input>.svg)")
    ap.add_argument("-t", "--title", help="schematic title")
    args = ap.parse_args(argv)

    nl = parse_file(args.netlist)
    pl = place(nl)
    title = args.title or os.path.splitext(os.path.basename(args.netlist))[0]
    svg = render(pl, nl, title=title)

    out = args.out or os.path.splitext(args.netlist)[0] + ".svg"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)

    print(f"parsed {len(nl.devices)} devices, {len(nl.nets)} nets")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
