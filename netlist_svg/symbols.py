"""Schematic symbol library (SVG fragments).

Every symbol is drawn inside a 64 x 92 local box and returns
``(svg_elements, terminals)`` with absolute coordinates.

Terminals:
    mos      -> 'T', 'B', 'G'
    res/diode-> 'T', 'B'
"""

from __future__ import annotations

BOX_W = 64
BOX_H = 92
CENTER_X = BOX_W / 2          # axis for 2-terminal devices

# ----- MOSFET geometry (gate on the LEFT before optional flip) -----
_CHANNEL_X = 30
_TERM_X = 46
_GATE_X = 0
_GATE_PLATE_X = 22
_GATE_Y = 46


def mos_term_local_x(flip: bool) -> float:
    return (BOX_W - _TERM_X) if flip else _TERM_X


def _arrow_x(x, y, dx):
    h, w = 6, 7
    tip, base = x + dx * w / 2, x - dx * w / 2
    return (f'<polygon points="{tip:.1f},{y:.1f} {base:.1f},{y-h/2:.1f} '
            f'{base:.1f},{y+h/2:.1f}" class="dev"/>')


def mosfet(ox, oy, mtype, source_side, flip):
    def X(x): return ox + (BOX_W - x if flip else x)
    def Y(y): return oy + y

    chan_x, term_x = X(_CHANNEL_X), X(_TERM_X)
    gate_x, plate_x = X(_GATE_X), X(_GATE_PLATE_X)

    e = []
    e.append(f'<line x1="{gate_x:.1f}" y1="{Y(_GATE_Y):.1f}" x2="{plate_x:.1f}" y2="{Y(_GATE_Y):.1f}" class="dev"/>')
    e.append(f'<line x1="{plate_x:.1f}" y1="{Y(26):.1f}" x2="{plate_x:.1f}" y2="{Y(66):.1f}" class="dev"/>')
    e.append(f'<line x1="{chan_x:.1f}" y1="{Y(24):.1f}" x2="{chan_x:.1f}" y2="{Y(68):.1f}" class="dev"/>')
    e.append(f'<line x1="{chan_x:.1f}" y1="{Y(30):.1f}" x2="{term_x:.1f}" y2="{Y(30):.1f}" class="dev"/>')
    e.append(f'<line x1="{term_x:.1f}" y1="{Y(30):.1f}" x2="{term_x:.1f}" y2="{Y(0):.1f}" class="dev"/>')
    e.append(f'<line x1="{chan_x:.1f}" y1="{Y(62):.1f}" x2="{term_x:.1f}" y2="{Y(62):.1f}" class="dev"/>')
    e.append(f'<line x1="{term_x:.1f}" y1="{Y(62):.1f}" x2="{term_x:.1f}" y2="{Y(BOX_H):.1f}" class="dev"/>')

    src_y = 30 if source_side == "T" else 62
    ax = (chan_x + term_x) / 2
    toward = 1 if chan_x < term_x else -1
    e.append(_arrow_x(ax, Y(src_y), toward if mtype == "nmos" else -toward))

    term = {"T": (term_x, Y(0)), "B": (term_x, Y(BOX_H)), "G": (gate_x, Y(_GATE_Y))}
    return e, term


def resistor(ox, oy, flip=False):
    """IEC box resistor, vertical, terminals top/bottom at center axis."""
    cx = ox + CENTER_X
    def Y(y): return oy + y
    bw = 16
    top, bot = 26, 66            # body extent
    e = []
    e.append(f'<line x1="{cx:.1f}" y1="{Y(0):.1f}" x2="{cx:.1f}" y2="{Y(top):.1f}" class="dev"/>')
    e.append(f'<rect x="{cx-bw/2:.1f}" y="{Y(top):.1f}" width="{bw:.1f}" height="{bot-top:.1f}" '
             f'rx="2" class="dev"/>')
    e.append(f'<line x1="{cx:.1f}" y1="{Y(bot):.1f}" x2="{cx:.1f}" y2="{Y(BOX_H):.1f}" class="dev"/>')
    return e, {"T": (cx, Y(0)), "B": (cx, Y(BOX_H))}


def diode(ox, oy, flip=False):
    """Diode, vertical, anode=T(top), cathode=B(bottom); conducts downward."""
    cx = ox + CENTER_X
    def Y(y): return oy + y
    tw = 18                       # triangle half-width*2
    ttop, tbot = 30, 58           # triangle from anode side down to bar
    e = []
    e.append(f'<line x1="{cx:.1f}" y1="{Y(0):.1f}" x2="{cx:.1f}" y2="{Y(ttop):.1f}" class="dev"/>')
    # triangle pointing down (anode -> cathode)
    e.append(f'<polygon points="{cx-tw/2:.1f},{Y(ttop):.1f} {cx+tw/2:.1f},{Y(ttop):.1f} '
             f'{cx:.1f},{Y(tbot):.1f}" class="devfill"/>')
    # cathode bar
    e.append(f'<line x1="{cx-tw/2:.1f}" y1="{Y(tbot):.1f}" x2="{cx+tw/2:.1f}" y2="{Y(tbot):.1f}" class="dev"/>')
    e.append(f'<line x1="{cx:.1f}" y1="{Y(tbot):.1f}" x2="{cx:.1f}" y2="{Y(BOX_H):.1f}" class="dev"/>')
    return e, {"T": (cx, Y(0)), "B": (cx, Y(BOX_H))}
