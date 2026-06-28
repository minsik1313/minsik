"""MOSFET schematic symbols as SVG fragments.

The symbol has three terminals: ``T`` (top), ``B`` (bottom) and ``G`` (gate).
The caller decides which of T/B is the source via ``source_side`` so that a
PMOS can be drawn source-up (toward VDD) and an NMOS source-down (toward VSS).
"""

from __future__ import annotations

# Local symbol geometry (gate on the LEFT, before optional horizontal flip).
BOX_W = 64
BOX_H = 92
_CHANNEL_X = 30
_TERM_X = 46
_GATE_X = 0
_GATE_PLATE_X = 22
_TOP_STUB_Y = 30
_BOT_STUB_Y = 62
_GATE_Y = 46


def _mirror_x(x: float) -> float:
    return BOX_W - x


def _arrow(x: float, y: float, dx: int) -> str:
    """Small filled triangle at (x,y) pointing in +/- x (dx = +1 or -1)."""
    h = 6
    w = 7
    tip = x + dx * (w / 2)
    base = x - dx * (w / 2)
    return (
        f'<polygon points="{tip:.1f},{y:.1f} {base:.1f},{y - h/2:.1f} '
        f'{base:.1f},{y + h/2:.1f}" class="dev"/>'
    )


def mosfet(ox: float, oy: float, mtype: str, source_side: str, flip: bool):
    """Return ``(svg_elements, terminals)`` for a MOSFET at origin (ox, oy).

    ``terminals`` maps 'T', 'B', 'G' to absolute (x, y) coordinates.
    """
    def X(x):
        return ox + (_mirror_x(x) if flip else x)

    def Y(y):
        return oy + y

    chan_x = X(_CHANNEL_X)
    term_x = X(_TERM_X)
    gate_x = X(_GATE_X)
    plate_x = X(_GATE_PLATE_X)

    elems = []
    # gate lead + plate
    elems.append(f'<line x1="{gate_x:.1f}" y1="{Y(_GATE_Y):.1f}" x2="{plate_x:.1f}" y2="{Y(_GATE_Y):.1f}" class="dev"/>')
    elems.append(f'<line x1="{plate_x:.1f}" y1="{Y(26):.1f}" x2="{plate_x:.1f}" y2="{Y(66):.1f}" class="dev"/>')
    # channel bar
    elems.append(f'<line x1="{chan_x:.1f}" y1="{Y(24):.1f}" x2="{chan_x:.1f}" y2="{Y(68):.1f}" class="dev"/>')
    # top stub
    elems.append(f'<line x1="{chan_x:.1f}" y1="{Y(_TOP_STUB_Y):.1f}" x2="{term_x:.1f}" y2="{Y(_TOP_STUB_Y):.1f}" class="dev"/>')
    elems.append(f'<line x1="{term_x:.1f}" y1="{Y(_TOP_STUB_Y):.1f}" x2="{term_x:.1f}" y2="{Y(0):.1f}" class="dev"/>')
    # bottom stub
    elems.append(f'<line x1="{chan_x:.1f}" y1="{Y(_BOT_STUB_Y):.1f}" x2="{term_x:.1f}" y2="{Y(_BOT_STUB_Y):.1f}" class="dev"/>')
    elems.append(f'<line x1="{term_x:.1f}" y1="{Y(_BOT_STUB_Y):.1f}" x2="{term_x:.1f}" y2="{Y(BOX_H):.1f}" class="dev"/>')

    # source arrow on the source stub
    src_stub_y = _TOP_STUB_Y if source_side == "T" else _BOT_STUB_Y
    ax = (chan_x + term_x) / 2
    # NMOS arrow points toward the channel, PMOS away from it.
    toward_channel = 1 if chan_x < term_x else -1
    dx = toward_channel if mtype == "nmos" else -toward_channel
    elems.append(_arrow(ax, Y(src_stub_y), dx))

    terminals = {
        "T": (term_x, Y(0)),
        "B": (term_x, Y(BOX_H)),
        "G": (gate_x, Y(_GATE_Y)),
    }
    return elems, terminals
