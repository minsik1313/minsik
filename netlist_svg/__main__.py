"""CLI: python -m netlist_svg <netlist.sp> [-o out.html] [-f html|svg]"""

from __future__ import annotations

import argparse
import os
import sys

from . import parse_file, place, render_svg, render_html


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert a SPICE netlist to an SVG/HTML schematic.")
    ap.add_argument("netlist", help="input SPICE netlist (.sp/.cir)")
    ap.add_argument("-o", "--out", help="output path (default: <input>.<fmt>)")
    ap.add_argument("-f", "--format", choices=["html", "svg"], default="html")
    ap.add_argument("-t", "--title", help="schematic title")
    args = ap.parse_args(argv)

    nl = parse_file(args.netlist)
    pl = place(nl)
    title = args.title or os.path.splitext(os.path.basename(args.netlist))[0]

    if args.format == "svg":
        out_text = render_svg(pl, nl, title=title)
    else:
        out_text = render_html(pl, nl, title=title)

    out = args.out or os.path.splitext(args.netlist)[0] + "." + args.format
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(out_text)

    print(f"parsed {len(nl.devices)} devices, {len(nl.nets)} nets")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
