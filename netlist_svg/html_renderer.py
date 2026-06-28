"""Wrap a schematic SVG in a self-contained HTML page with a library panel."""

from __future__ import annotations

import html

from . import symbols
from .renderer import _STYLE, render_svg

_GLYPHS = {
    "nmos":     ("NMOS",     lambda: symbols.mosfet(0, 0, "nmos", "B", False)),
    "pmos":     ("PMOS",     lambda: symbols.mosfet(0, 0, "pmos", "T", False)),
    "resistor": ("Resistor", lambda: symbols.resistor(0, 0)),
}


def _glyph_svg(maker):
    elems, _ = maker()
    body = "".join(elems)
    return (f'<svg width="46" height="66" viewBox="-6 -4 76 100">'
            f'<style>{_STYLE}</style>{body}</svg>')


def _device_kind_key(d):
    if d.kind == "mos":
        return d.mtype
    if d.kind == "res":
        return "resistor"
    return d.kind


def _library_panel(netlist):
    groups = {}
    for d in netlist.devices:
        groups.setdefault(_device_kind_key(d), []).append(d.name)

    rows = []
    for key, (label, maker) in _GLYPHS.items():
        if key not in groups:
            continue
        names = ", ".join(sorted(groups[key]))
        rows.append(
            f'<div class="lib-item">'
            f'<div class="lib-glyph">{_glyph_svg(maker)}</div>'
            f'<div class="lib-meta"><div class="lib-name">{label} '
            f'<span class="lib-count">×{len(groups[key])}</span></div>'
            f'<div class="lib-insts">{names}</div></div></div>'
        )
    return "\n".join(rows)


def _netlist_panel(netlist):
    lines = []
    for raw in netlist.source.splitlines():
        esc = html.escape(raw)
        cls = "nl-comment" if raw.strip().startswith("*") else "nl-line"
        lines.append(f'<span class="{cls}">{esc or "&nbsp;"}</span>')
    return "<pre class=\"nl\">" + "\n".join(lines) + "</pre>"


def render_html(placement, netlist, title="schematic"):
    svg = render_svg(placement, netlist, title=title)
    panel = _library_panel(netlist)
    netlist_src = _netlist_panel(netlist)
    nets = ", ".join(sorted(netlist.nets))

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ margin:0; font-family:'DejaVu Sans',sans-serif; color:#222; background:#f5f6f8; }}
  header {{ background:#1b3a5b; color:#fff; padding:14px 22px; }}
  header h1 {{ margin:0; font-size:18px; }}
  header .sub {{ font-size:12px; opacity:.8; margin-top:4px; }}
  .layout {{ display:flex; gap:18px; padding:18px; align-items:flex-start; }}
  .schematic {{ background:#fff; border:1px solid #dcdfe4; border-radius:8px;
               padding:10px; overflow:auto; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .panel {{ width:330px; flex:0 0 330px; background:#fff; border:1px solid #dcdfe4;
            border-radius:8px; padding:14px; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .panel h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.5px;
               color:#1b3a5b; margin:0 0 10px; }}
  .lib-item {{ display:flex; gap:10px; align-items:center; padding:8px 0;
               border-bottom:1px solid #eef0f3; }}
  .lib-glyph {{ flex:0 0 46px; text-align:center; }}
  .lib-name {{ font-weight:bold; font-size:13px; }}
  .lib-count {{ color:#2e7d32; font-weight:normal; }}
  .lib-insts {{ font-size:11px; color:#666; margin-top:2px; }}
  .nets {{ font-size:11px; color:#666; margin-top:12px; line-height:1.5; }}
  .nl {{ margin:0; font-family:'DejaVu Sans Mono',monospace; font-size:11.5px;
         line-height:1.5; white-space:pre; overflow-x:auto;
         background:#0f2233; color:#dfe7ef; padding:12px; border-radius:6px; }}
  .nl-comment {{ color:#6f8aa3; }}
  .nl-line {{ color:#e8eef4; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="sub">netlist → SVG/HTML schematic · auto-placement</div>
</header>
<div class="layout">
  <div class="schematic">{svg}</div>
  <aside class="panel">
    <h2>Netlist</h2>
    {netlist_src}
    <h2 style="margin-top:18px">Component Library</h2>
    {panel}
    <div class="nets"><b>Nets:</b> {nets}</div>
  </aside>
</div>
</body>
</html>
"""
