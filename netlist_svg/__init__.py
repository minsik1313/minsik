"""netlist_svg: convert SPICE MOSFET netlists into SVG schematics."""

from .parser import parse, parse_file, Netlist, Device
from .placer import place, Placement
from .renderer import render

__all__ = ["parse", "parse_file", "Netlist", "Device", "place", "Placement", "render", "convert"]


def convert(text: str, title: str = "schematic") -> str:
    """Parse SPICE ``text`` and return an SVG string."""
    nl = parse(text)
    pl = place(nl)
    return render(pl, nl, title=title)
