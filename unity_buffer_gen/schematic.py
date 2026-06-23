"""Render the unity-gain buffer netlist as an annotated schematic.

Produces a hand-laid-out SVG (deterministic, no layout engine) of the
NMOS-input 5T OTA + PMOS pass topology, with every device labelled by its
sky130 sizing (W/L, nf, m) and optional operating-point values.  If a raster
backend (cairosvg) is available a PNG is also written.
"""

from __future__ import annotations

import os
from .spec import DeviceSizes, BiasPlan, BufferSpec


# ---- primitive SVG helpers -------------------------------------------------

def _line(x1, y1, x2, y2, color="#000", w=2, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{w}"{da}/>')


def _poly(pts, color="#000", w=2):
    p = " ".join(f"{x},{y}" for x, y in pts)
    return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{w}"/>'


def _dot(x, y, r=4, color="#000"):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def _circ(x, y, r, color="#000", w=2):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{color}" stroke-width="{w}"/>'


def _text(x, y, s, size=13, color="#000", anchor="start", weight="normal"):
    out = []
    for i, ln in enumerate(s.split("\n")):
        out.append(f'<text x="{x}" y="{y + i*(size+2)}" font-size="{size}" '
                   f'fill="{color}" text-anchor="{anchor}" '
                   f'font-family="sans-serif" font-weight="{weight}">{ln}</text>')
    return "".join(out)


# MOSFET symbol. Centered at (cx,cy); H tall. drain=top, source=bottom,
# gate lead exits on `gate` side ('l' or 'r'). pmos adds the gate bubble.
def _mosfet(cx, cy, name, sizing, pmos=False, gate="l", color="#000"):
    H = 56
    top = cy - H / 2
    bot = cy + H / 2
    ch_x = cx                      # channel (drain-source) vertical line
    g_x = cx - 16 if gate == "l" else cx + 16   # gate plate
    s = []
    # drain & source leads + channel fingers
    s.append(_line(ch_x, top, ch_x, top + 12, color))          # drain lead
    s.append(_line(ch_x, bot, ch_x, bot - 12, color))          # source lead
    s.append(_line(ch_x, top + 12, g_x + (8 if gate == "l" else -8), top + 12, color))
    s.append(_line(ch_x, cy, g_x + (8 if gate == "l" else -8), cy, color))
    s.append(_line(ch_x, bot - 12, g_x + (8 if gate == "l" else -8), bot - 12, color))
    # gate plate
    s.append(_line(g_x, top + 6, g_x, bot - 6, color, 2.5))
    # gate lead out
    lead_end = g_x - 22 if gate == "l" else g_x + 22
    bub_r = 5
    if pmos:
        bx = g_x - bub_r if gate == "l" else g_x + bub_r
        s.append(_circ(bx, cy, bub_r, color))
        s.append(_line(bx - bub_r if gate == "l" else bx + bub_r, cy, lead_end, cy, color))
    else:
        s.append(_line(g_x, cy, lead_end, cy, color))
    # labels
    lx = cx + 22
    s.append(_text(lx, cy - 4, name, 13, "#000", "start", "bold"))
    s.append(_text(lx, cy + 13, sizing, 11, "#333", "start"))
    return "".join(s), {"d": (ch_x, top), "s": (ch_x, bot), "g": (lead_end, cy)}


def _sizing(L, W, nf, m):
    return f"{W:g}/{L:g} nf{nf}×m{m}"


def render_svg(spec: BufferSpec, sz: DeviceSizes, bias: BiasPlan) -> str:
    W, Hc = 1180, 760
    VDD, VSS = 70, 700
    el = []

    # rails
    el.append(_line(40, VDD, 1140, VDD, "#c00", 3))
    el.append(_text(34, VDD - 8, f"VDD = {spec.vdd:g} V", 14, "#c00", "start", "bold"))
    el.append(_line(40, VSS, 1140, VSS, "#000", 3))
    el.append(_text(34, VSS + 22, "VSS / GND", 14, "#000", "start", "bold"))

    def to_rail(term, y):
        el.append(_line(term[0], term[1], term[0], y))

    # ---- OTA: PMOS mirror M3/M4 (top), NMOS pair M1/M2, tail MB1 ----
    m3, m3t = _mosfet(330, 165, "M3", _sizing(sz.lm, sz.wm, sz.nfm, sz.mm), pmos=True, gate="l")
    m4, m4t = _mosfet(500, 165, "M4", _sizing(sz.lm, sz.wm, sz.nfm, sz.mm), pmos=True, gate="r")
    m1, m1t = _mosfet(330, 330, "M1", _sizing(sz.li, sz.wi, sz.nfi, sz.mi), gate="l")
    m2, m2t = _mosfet(500, 330, "M2", _sizing(sz.li, sz.wi, sz.nfi, sz.mi), gate="r")
    mb1, mb1t = _mosfet(415, 500, "MB1", _sizing(sz.lb, sz.wb, sz.nfb, sz.mb_tail), gate="l")
    el += [m3, m4, m1, m2, mb1]

    to_rail(m3t["s"], VDD); to_rail(m4t["s"], VDD)
    # NA = M3.d = M1.d ; OTA = M4.d = M2.d
    na = (330, (m3t["d"][1] + m1t["d"][1]) / 2)
    el.append(_line(*m3t["d"], m1t["d"][0], m1t["d"][1]))
    el.append(_dot(*na)); el.append(_text(348, na[1] + 4, "NA", 12, "#000"))
    ota = (500, (m4t["d"][1] + m2t["d"][1]) / 2)
    el.append(_line(*m4t["d"], m2t["d"][0], m2t["d"][1]))
    el.append(_dot(*ota)); el.append(_text(515, ota[1] + 4, "OTA", 12, "#070"))
    # mirror gates tied to NA
    el.append(_poly([m3t["g"], (m3t["g"][0] - 12, m3t["g"][1]),
                     (m3t["g"][0] - 12, na[1]), na]))
    el.append(_poly([m4t["g"], (m4t["g"][0] + 14, m4t["g"][1]),
                     (m4t["g"][0] + 14, na[1] - 10), (na[0], na[1] - 10)]))
    # TAIL
    tail = (415, (m1t["s"][1] + mb1t["d"][1]) / 2)
    el.append(_line(m1t["s"][0], m1t["s"][1], 415, m1t["s"][1]))
    el.append(_line(m2t["s"][0], m2t["s"][1], 415, m2t["s"][1]))
    el.append(_line(415, m1t["s"][1], 415, mb1t["d"][1]))
    el.append(_dot(*tail)); el.append(_text(430, tail[1] - 4, "TAIL", 12))
    to_rail(mb1t["s"], VSS)

    # input gates: M1.g = VOUT(fb), M2.g = VREF
    el.append(_line(m1t["g"][0], m1t["g"][1], m1t["g"][0] - 28, m1t["g"][1], "#06c"))
    el.append(_text(m1t["g"][0] - 32, m1t["g"][1] + 4, "VOUT (fb)", 12, "#06c", "end", "bold"))
    el.append(_line(m2t["g"][0], m2t["g"][1], m2t["g"][0] + 28, m2t["g"][1]))
    el.append(_text(m2t["g"][0] + 32, m2t["g"][1] + 4, f"VREF {spec.vref:g}V", 12, "#000"))

    # ---- bias diode MB0 + IREF ----
    mb0, mb0t = _mosfet(150, 500, "MB0", _sizing(sz.lb, sz.wb, sz.nfb, sz.mb_ref), gate="l")
    el.append(mb0); to_rail(mb0t["s"], VSS)
    ib = mb0t["d"]
    el.append(_dot(*ib)); el.append(_text(ib[0] + 8, ib[1] - 6, "IBIAS", 12))
    el.append(_poly([mb0t["g"], (mb0t["g"][0] - 10, mb0t["g"][1]),
                     (mb0t["g"][0] - 10, ib[1]), ib]))
    # IREF source VDD->IBIAS
    el.append(_circ(150, 300, 18))
    el.append(_line(150, VDD, 150, 282)); el.append(_line(150, 318, 150, ib[1]))
    el.append(_poly([(150, 293), (150, 307)]))   # arrow stem
    el.append(f'<polygon points="150,290 145,300 155,300" fill="#000"/>')
    el.append(_text(172, 296, "IREF", 12)); el.append(_text(172, 311, f"{bias.iref*1e6:g}uA", 11, "#333"))
    # IBIAS distribution to MB1.g and MBPRE.g via a low bus
    busy = 560
    el.append(_line(ib[0], ib[1], ib[0], busy, "#000", 1.6, "4,3"))
    el.append(_line(ib[0], busy, 1010, busy, "#000", 1.6, "4,3"))
    el.append(_poly([mb1t["g"], (mb1t["g"][0] - 10, mb1t["g"][1]),
                     (mb1t["g"][0] - 10, busy)], "#000", 1.6))

    # ---- pass MP + output ----
    mp, mpt = _mosfet(800, 165, "MP", _sizing(sz.lp, sz.wp, sz.nfp, sz.mp), pmos=True, gate="l")
    el.append(mp); to_rail(mpt["s"], VDD)
    # OTA -> MP gate (green)
    el.append(_poly([ota, (640, ota[1]), (640, mpt["g"][1]), mpt["g"]], "#070", 2.2))
    # VOUT node
    vout = (800, 300)
    el.append(_line(mpt["d"][0], mpt["d"][1], 800, 300))
    el.append(_dot(*vout)); el.append(_text(815, 296, f"VOUT = {spec.vout:g} V", 14, "#06c", "start", "bold"))
    # VOUT bus to COUT and MBPRE
    el.append(_line(800, 300, 1010, 300))
    # COUT
    el.append(_line(910, 300, 910, 360))
    el.append(_line(885, 360, 935, 360, "#000", 2.5)); el.append(_line(885, 374, 935, 374, "#000", 2.5))
    el.append(_line(910, 374, 910, VSS))
    el.append(_text(942, 363, "COUT", 12)); el.append(_text(942, 378, f"{spec.cout*1e6:g}uF", 11, "#333"))
    # MBPRE
    mbpre, mbt = _mosfet(1010, 500, "MBPRE", _sizing(sz.lb, sz.wb, sz.nfb, sz.mb_pre), gate="r")
    el.append(mbpre); to_rail(mbt["s"], VSS)
    el.append(_line(mbt["d"][0], mbt["d"][1], 1010, 300))
    el.append(_poly([mbt["g"], (mbt["g"][0] + 10, mbt["g"][1]),
                     (mbt["g"][0] + 10, busy)], "#000", 1.6))

    # feedback VOUT -> M1.gate routed along the bottom (blue)
    fb_y = 660
    el.append(_poly([vout, (800, fb_y), (m1t["g"][0] - 28, fb_y),
                     (m1t["g"][0] - 28, m1t["g"][1])], "#06c", 2))

    # title
    el.append(_text(20, 28, "sky130 unity-gain buffer (LDO follower) — W/L in µm, nf fingers, m multiplier", 15, "#000", "start", "bold"))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hc}" '
           f'viewBox="0 0 {W} {Hc}"><rect width="{W}" height="{Hc}" fill="#fff"/>'
           + "".join(el) + "</svg>")
    return svg


def draw(spec: BufferSpec, sz: DeviceSizes, bias: BiasPlan,
         out_path: str) -> str:
    """Write the schematic SVG to out_path; also write a PNG if possible."""
    svg = render_svg(spec, sz, bias)
    svg_path = os.path.splitext(out_path)[0] + ".svg"
    with open(svg_path, "w") as fh:
        fh.write(svg)
    if out_path.endswith(".png"):
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode(), write_to=out_path, scale=1.4)
            return out_path
        except Exception:
            pass
    return svg_path
