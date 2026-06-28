"""netlist_svg: convert SPICE netlists into SVG/HTML schematics."""

from .parser import parse, parse_file, Netlist, Device
from .placer import place, Placement
from .renderer import render_svg, render
from .html_renderer import render_html

__all__ = [
    "parse", "parse_file", "Netlist", "Device",
    "place", "Placement",
    "render_svg", "render", "render_html",
    "convert",
]


def convert(text, title="schematic", fmt="html"):
    """Parse SPICE ``text`` and return an SVG or HTML string."""
    nl = parse(text)
    pl = place(nl)
    if fmt == "svg":
        return render_svg(pl, nl, title=title)
    return render_html(pl, nl, title=title)
