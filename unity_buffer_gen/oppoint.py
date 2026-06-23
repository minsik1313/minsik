"""Extract per-device operating-point and small-signal values from ngspice.

For every transistor in the buffer this reports the geometry settings
(W/L/nf/m), the bias point (Id, Vgs, Vds, Vth) and the small-signal values the
user usually wants: transconductance gm, output resistance ro = 1/gds and the
terminal capacitances (Cgg/Cgs/Cgd).  Run at a chosen load current.
"""

from __future__ import annotations

import os
import re
import subprocess

from .spec import BufferSpec, DeviceSizes, BiasPlan
from . import netlist as nl

# (instance, model-short, geometry-attrs) in schematic order
DEVICES = [
    ("MB0", "nfet", ("lb", "wb", "nfb", "mb_ref"), "bias diode"),
    ("MB1", "nfet", ("lb", "wb", "nfb", "mb_tail"), "tail current src"),
    ("MBPRE", "nfet", ("lb", "wb", "nfb", "mb_pre"), "output preload"),
    ("M1", "nfet", ("li", "wi", "nfi", "mi"), "input (g=VOUT)"),
    ("M2", "nfet", ("li", "wi", "nfi", "mi"), "input (g=VREF)"),
    ("M3", "pfet", ("lm", "wm", "nfm", "mm"), "mirror diode"),
    ("M4", "pfet", ("lm", "wm", "nfm", "mm"), "mirror out"),
    ("MP", "pfet", ("lp", "wp", "nfp", "mp"), "pass device"),
]
PARAMS = ["id", "vgs", "vds", "vth", "vdsat", "gm", "gds", "cgg", "cgs", "cgd"]


def extract(pdk, spec: BufferSpec, sz: DeviceSizes, bias: BiasPlan,
            iload: float, workdir: str) -> dict:
    """Return {inst: {param: value, ...}} at the given load current."""
    lines = [f'.lib "{pdk.lib_path}" {spec.corner}', ".option scale=1.0u",
             nl.buffer_subckt(sz),
             f"VDD VDD 0 {spec.vdd:g}", f"VREF VREF 0 {spec.vref:g}",
             f"IREF VDD IBIAS {bias.iref:g}",
             "XBUF VDD 0 VREF VOUT IBIAS unity_buffer",
             f"COUT VOUT 0 {spec.cout:g}", f"ILOAD VOUT 0 {iload:g}",
             nl._nodeset(spec), ".control", "op"]
    for inst, mod, _, _ in DEVICES:
        full = f"sky130_fd_pr__{mod}_01v8"
        for p in PARAMS:
            lines.append(f"print @m.xbuf.x{inst.lower()}.m{full}[{p}]")
    lines += [".endc", ".end"]
    os.makedirs(workdir, exist_ok=True)
    deck = os.path.join(workdir, "oppoint.spice")
    with open(deck, "w") as fh:
        fh.write("\n".join(lines))
    r = subprocess.run(["ngspice", "-b", "oppoint.spice"], cwd=workdir,
                       capture_output=True, text=True, timeout=120)
    vals = {}
    for line in r.stdout.splitlines():
        m = re.search(r"\.x(\w+)\.m\w+\[(\w+)\]\s*=\s*([-\d.eE+]+)", line)
        if m:
            vals.setdefault(m.group(1).upper(), {})[m.group(2)] = float(m.group(3))
    return vals


def device_table_md(spec, sz, bias, vals: dict) -> str:
    """Markdown table of geometry + operating point for each device."""
    L = []
    L.append("| Device | Role | Model | W/L (µm) | nf×m | Id | Vgs (V) | Vds (V) "
             "| gm | ro=1/gds | Cgg (fF) | Cgd (fF) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for inst, mod, attrs, role in DEVICES:
        l, w, nf, m = (getattr(sz, a) for a in attrs)
        d = vals.get(inst, {})
        idv = d.get("id", 0.0)
        id_s = f"{idv*1e3:.2f} mA" if abs(idv) >= 1e-3 else f"{idv*1e6:.1f} µA"
        gm = d.get("gm", 0.0)
        gm_s = f"{gm*1e3:.1f} mS" if gm >= 1e-3 else f"{gm*1e6:.0f} µS"
        gds = d.get("gds", 0.0)
        ro = (1.0 / gds) if gds else float("inf")
        ro_s = (f"{ro/1e6:.2f} MΩ" if ro >= 1e6 else
                f"{ro/1e3:.1f} kΩ" if ro >= 1e3 else f"{ro:.1f} Ω")
        L.append(f"| {inst} | {role} | {mod}_01v8 | {w:g}/{l:g} | {nf}×{m} | "
                 f"{id_s} | {d.get('vgs',0):.3f} | {d.get('vds',0):.3f} | "
                 f"{gm_s} | {ro_s} | {abs(d.get('cgg',0))*1e15:.0f} | "
                 f"{abs(d.get('cgd',0))*1e15:.1f} |")
    return "\n".join(L)


def passives_md(spec, bias) -> str:
    L = ["| Component | Value | Notes |", "|---|---|---|"]
    L.append(f"| COUT | {spec.cout*1e6:g} µF (ESR {spec.cout_esr:g} Ω) | output cap, sets dominant pole |")
    L.append(f"| IREF | {bias.iref*1e6:g} µA | external reference current into IBIAS |")
    L.append(f"| Itail | {bias.itail*1e6:g} µA | OTA tail (mirrored from IREF) |")
    L.append(f"| Ipreload | ~{bias.ipreload*1e6:g} µA | internal MBPRE sink at VOUT |")
    L.append(f"| error_res (target) | {spec.error_res:g} Ω | spec: ΔVout/ΔIload |")
    L.append("| (discrete resistors) | none | output resistance is the "
             "closed-loop ro; no passive R in the cell |")
    return "\n".join(L)
