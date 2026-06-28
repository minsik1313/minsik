"""Render a Placement into an SVG schematic (and an HTML page wrapper)."""

from __future__ import annotations

from collections import defaultdict

from . import symbols
from .placer import classify_net
from .symbols import BOX_H

MARGIN_TOP = 80
MARGIN_BOTTOM = 80
MARGIN_LEFT = 160
MARGIN_RIGHT = 160
LEVEL_H = 150
COL_W = 200
PORT_LEN = 60

_STYLE = """
  .dev   { stroke:#1b3a5b; stroke-width:2.2; fill:none; }
  .devfill { fill:#1b3a5b; stroke:none; }
  polygon.dev { fill:#1b3a5b; stroke:none; }
  .wire  { stroke:#2e7d32; stroke-width:2; fill:none; }
  .rail  { stroke:#b71c1c; stroke-width:3; fill:none; }
  .dot   { fill:#2e7d32; }
  .lbl   { font-family:'DejaVu Sans',sans-serif; font-size:13px; fill:#222; }
  .devlbl{ font-family:'DejaVu Sans',sans-serif; font-size:13px; fill:#1b3a5b; font-weight:bold; }
  .vallbl{ font-family:'DejaVu Sans',sans-serif; font-size:11px; fill:#555; }
  .raillbl{ font-family:'DejaVu Sans',sans-serif; font-size:14px; fill:#b71c1c; font-weight:bold; }
  .port  { fill:#fff; stroke:#2e7d32; stroke-width:2; }
"""


def _net_y(level):
    return MARGIN_TOP + level * LEVEL_H


def _x_center(col):
    return MARGIN_LEFT + col * COL_W


def _is_port(netlist, net):
    """Signal net that only appears on gates (never a power terminal)."""
    for d in netlist.devices:
        if net in d.power_terminals():
            return False
    return True


def _draw_symbol(d, ox, oy, flip, source_side):
    if d.kind == "mos":
        return symbols.mosfet(ox, oy, d.mtype, source_side, flip)
    if d.kind == "res":
        return symbols.resistor(ox, oy, flip)
    if d.kind == "diode":
        return symbols.diode(ox, oy, flip)
    raise ValueError(d.kind)


def render_svg(placement, netlist, title="schematic"):
    elems = []
    pin_points = defaultdict(list)

    # horizontal track per net (rails flat; same-level signal nets fanned out)
    level_nets = defaultdict(list)
    track_y = {}
    for net in netlist.nets:
        if classify_net(net) == "signal":
            level_nets[placement.net_level[net]].append(net)
        else:
            track_y[net] = _net_y(placement.net_level[net])
    for lvl, nets in level_nets.items():
        nets_sorted = sorted(nets, key=lambda n: placement.col_of.get(n, 0))
        k = len(nets_sorted)
        for i, net in enumerate(nets_sorted):
            track_y[net] = _net_y(lvl) + (i - (k - 1) / 2) * 26

    # ---- devices ----
    for pd in placement.devices:
        d = pd.device
        p0, p1 = d.power_terminals()
        l0, l1 = placement.net_level[p0], placement.net_level[p1]
        top_net = p0 if l0 <= l1 else p1
        bot_net = p1 if l0 <= l1 else p0
        source_side = "T" if (d.kind == "mos" and d.mtype == "pmos") else "B"

        x_center = _x_center(pd.col)
        term_local = symbols.mos_term_local_x(flip=pd.flip) if d.kind == "mos" else symbols.CENTER_X
        ox = x_center - term_local
        oy = _net_y(min(l0, l1)) + (LEVEL_H - BOX_H) / 2

        svg, term = _draw_symbol(d, ox, oy, pd.flip, source_side)
        elems.extend(svg)

        # power-terminal leads
        tx, ty = term["T"]
        bx, by = term["B"]
        elems.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx:.1f}" y2="{track_y[top_net]:.1f}" class="wire"/>')
        elems.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx:.1f}" y2="{track_y[bot_net]:.1f}" class="wire"/>')
        pin_points[top_net].append((tx, track_y[top_net]))
        pin_points[bot_net].append((bx, track_y[bot_net]))

        # labels
        if d.kind == "mos":
            anchor = "end" if not pd.flip else "start"
            lx = term["G"][0] + (-6 if not pd.flip else 6)
            elems.append(f'<text class="devlbl" x="{lx:.1f}" y="{oy + 18:.1f}" text-anchor="{anchor}">{d.name}</text>')
        else:
            elems.append(f'<text class="devlbl" x="{x_center + 14:.1f}" y="{oy + 40:.1f}" text-anchor="start">{d.name}</text>')
            extra = d.value or d.model
            if extra:
                elems.append(f'<text class="vallbl" x="{x_center + 14:.1f}" y="{oy + 56:.1f}" text-anchor="start">{extra}</text>')

        # gate (mos only)
        if d.kind == "mos":
            gx, gy = term["G"]
            gnet = d.gate
            direction = -1 if not pd.flip else 1
            if classify_net(gnet) == "signal" and _is_port(netlist, gnet):
                px = gx + direction * PORT_LEN
                elems.append(f'<line x1="{gx:.1f}" y1="{gy:.1f}" x2="{px:.1f}" y2="{gy:.1f}" class="wire"/>')
                elems.append(f'<circle cx="{px:.1f}" cy="{gy:.1f}" r="4" class="port"/>')
                a = "end" if direction < 0 else "start"
                elems.append(f'<text class="lbl" x="{px + direction * 8:.1f}" y="{gy - 8:.1f}" text-anchor="{a}">{gnet}</text>')
            else:
                stub_x = gx + direction * 18
                elems.append(f'<line x1="{gx:.1f}" y1="{gy:.1f}" x2="{stub_x:.1f}" y2="{gy:.1f}" class="wire"/>')
                elems.append(f'<line x1="{stub_x:.1f}" y1="{gy:.1f}" x2="{stub_x:.1f}" y2="{track_y[gnet]:.1f}" class="wire"/>')
                pin_points[gnet].append((stub_x, track_y[gnet]))

    # ---- net trunks & rails ----
    width = MARGIN_LEFT + (placement.n_cols - 1) * COL_W + MARGIN_RIGHT
    for net, pts in pin_points.items():
        if not pts:
            continue
        cls = classify_net(net)
        ys = track_y[net]
        xs = [p[0] for p in pts]
        x0, x1 = min(xs), max(xs)
        if cls in ("vdd", "gnd"):
            x0, x1 = MARGIN_LEFT - 110, width - MARGIN_RIGHT + 110
            elems.insert(0, f'<line x1="{x0:.1f}" y1="{ys:.1f}" x2="{x1:.1f}" y2="{ys:.1f}" class="rail"/>')
            dy = -8 if cls == "vdd" else 18
            elems.append(f'<text class="raillbl" x="{x0:.1f}" y="{ys + dy:.1f}">{net}</text>')
        else:
            elems.insert(0, f'<line x1="{x0:.1f}" y1="{ys:.1f}" x2="{x1:.1f}" y2="{ys:.1f}" class="wire"/>')
            elems.append(f'<text class="lbl" x="{(x0 + x1) / 2:.1f}" y="{ys - 7:.1f}" text-anchor="middle">{net}</text>')
        if len(pts) >= 3:
            for (px, _py) in dict.fromkeys(pts):   # dedupe coincident pins
                elems.append(f'<circle cx="{px:.1f}" cy="{ys:.1f}" r="3.2" class="dot"/>')

    height = MARGIN_TOP + placement.max_level * LEVEL_H + MARGIN_BOTTOM
    body = "\n  ".join(elems)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">\n'
        f'<style>{_STYLE}</style>\n'
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#ffffff"/>\n'
        f'<text class="lbl" x="10" y="22" font-size="16">{title}</text>\n'
        f'  {body}\n</svg>\n'
    )


# Backwards-compatible name.
def render(placement, netlist, title="schematic"):
    return render_svg(placement, netlist, title=title)
