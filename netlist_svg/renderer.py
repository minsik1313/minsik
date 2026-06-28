"""Render a Placement into an SVG schematic."""

from __future__ import annotations

from . import symbols
from .placer import classify_net
from .symbols import BOX_H, BOX_W

# layout constants
MARGIN_TOP = 80
MARGIN_BOTTOM = 80
MARGIN_LEFT = 150
MARGIN_RIGHT = 150
LEVEL_H = 150
COL_W = 220
PORT_LEN = 60

_STYLE = """
  .dev   { stroke:#1b3a5b; stroke-width:2.2; fill:none; }
  polygon.dev { fill:#1b3a5b; stroke:none; }
  .wire  { stroke:#2e7d32; stroke-width:2; fill:none; }
  .rail  { stroke:#b71c1c; stroke-width:3; fill:none; }
  .dot   { fill:#2e7d32; }
  .lbl   { font-family:'DejaVu Sans',sans-serif; font-size:13px; fill:#222; }
  .devlbl{ font-family:'DejaVu Sans',sans-serif; font-size:13px; fill:#1b3a5b; font-weight:bold; }
  .raillbl{ font-family:'DejaVu Sans',sans-serif; font-size:14px; fill:#b71c1c; font-weight:bold; }
  .port  { fill:#fff; stroke:#2e7d32; stroke-width:2; }
"""


def _net_y(level: int) -> float:
    return MARGIN_TOP + level * LEVEL_H


def _x_center(col: float) -> float:
    return MARGIN_LEFT + col * COL_W


def render(placement, netlist, title="schematic") -> str:
    elems = []
    pin_points = {}   # net -> list of (x, y) connection points on its trunk

    def add_pin(net, pt):
        pin_points.setdefault(net, []).append(pt)

    # Give each net a horizontal "track" y.  Power rails stay flat; signal nets
    # that land on the same level are fanned out vertically so two different
    # nets never share one collinear wire (which would read as a short).
    from collections import defaultdict
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

    # ---- place devices ----
    for pd in placement.devices:
        d = pd.device
        ld, ls = placement.net_level[d.drain], placement.net_level[d.source]
        top_net = d.drain if ld <= ls else d.source
        bot_net = d.source if ld <= ls else d.drain
        source_side = "B" if d.mtype == "nmos" else "T"

        # vertical placement: body centered between the two net levels
        top_y = _net_y(min(ld, ls))
        x_center = _x_center(pd.col)
        # align the drain/source terminal column to x_center
        term_local = symbols.BOX_W - symbols._TERM_X if pd.flip else symbols._TERM_X
        ox = x_center - term_local
        oy = top_y + (LEVEL_H - BOX_H) / 2

        svg, term = symbols.mosfet(ox, oy, d.mtype, source_side, pd.flip)
        elems.extend(svg)

        # device label
        elems.append(
            f'<text class="devlbl" x="{term["G"][0] + (-6 if not pd.flip else 6):.1f}" '
            f'y="{oy + 18:.1f}" text-anchor="{"end" if not pd.flip else "start"}">'
            f'{d.name}</text>'
        )

        # connect terminals to their net trunks (vertical leads)
        tx, ty = term["T"]
        bx, by = term["B"]
        ty_net = track_y[top_net]
        by_net = track_y[bot_net]
        elems.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx:.1f}" y2="{ty_net:.1f}" class="wire"/>')
        elems.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx:.1f}" y2="{by_net:.1f}" class="wire"/>')
        add_pin(top_net, (tx, ty_net))
        add_pin(bot_net, (bx, by_net))

        # gate
        gx, gy = term["G"]
        gate_net = d.gate
        if classify_net(gate_net) == "signal" and _is_port(netlist, gate_net):
            # external input port
            direction = -1 if not pd.flip else 1
            px = gx + direction * PORT_LEN
            elems.append(f'<line x1="{gx:.1f}" y1="{gy:.1f}" x2="{px:.1f}" y2="{gy:.1f}" class="wire"/>')
            elems.append(f'<circle cx="{px:.1f}" cy="{gy:.1f}" r="4" class="port"/>')
            anchor = "end" if direction < 0 else "start"
            lx = px + direction * 8
            elems.append(f'<text class="lbl" x="{lx:.1f}" y="{gy - 8:.1f}" text-anchor="{anchor}">{gate_net}</text>')
        else:
            # gate joins an internal net trunk: stub out then drop to trunk
            direction = -1 if not pd.flip else 1
            stub_x = gx + direction * 18
            trunk_y = track_y[gate_net]
            elems.append(f'<line x1="{gx:.1f}" y1="{gy:.1f}" x2="{stub_x:.1f}" y2="{gy:.1f}" class="wire"/>')
            elems.append(f'<line x1="{stub_x:.1f}" y1="{gy:.1f}" x2="{stub_x:.1f}" y2="{trunk_y:.1f}" class="wire"/>')
            add_pin(gate_net, (stub_x, trunk_y))

    # ---- draw net trunks & rails ----
    width = MARGIN_LEFT + (placement.n_cols - 1) * COL_W + MARGIN_RIGHT
    for net, pts in pin_points.items():
        if not pts:
            continue
        cls = classify_net(net)
        ys = track_y[net]
        xs = [p[0] for p in pts]
        x0, x1 = min(xs), max(xs)
        if cls == "vdd":
            x0, x1 = MARGIN_LEFT - 100, width - MARGIN_RIGHT + 100
            elems.insert(0, f'<line x1="{x0:.1f}" y1="{ys:.1f}" x2="{x1:.1f}" y2="{ys:.1f}" class="rail"/>')
            elems.append(f'<text class="raillbl" x="{x0:.1f}" y="{ys - 8:.1f}">{net}</text>')
        elif cls == "gnd":
            x0, x1 = MARGIN_LEFT - 100, width - MARGIN_RIGHT + 100
            elems.insert(0, f'<line x1="{x0:.1f}" y1="{ys:.1f}" x2="{x1:.1f}" y2="{ys:.1f}" class="rail"/>')
            elems.append(f'<text class="raillbl" x="{x0:.1f}" y="{ys + 18:.1f}">{net}</text>')
        else:
            elems.insert(0, f'<line x1="{x0:.1f}" y1="{ys:.1f}" x2="{x1:.1f}" y2="{ys:.1f}" class="wire"/>')
            # net name label near the trunk
            elems.append(f'<text class="lbl" x="{(x0 + x1) / 2:.1f}" y="{ys - 7:.1f}" text-anchor="middle">{net}</text>')
        # junction dots when 3+ pins meet
        if len(pts) >= 3:
            for (px, _py) in pts:
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


def _is_port(netlist, net) -> bool:
    """A signal net that only ever appears on gates is an external port."""
    for d in netlist.devices:
        if net in (d.drain, d.source):
            return False
    return True
