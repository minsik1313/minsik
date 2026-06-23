"""SPICE netlist construction for the sky130 unity-gain buffer.

Topology (capacitor-stabilized voltage follower / LDO):

      VDD ---+----------+-------------------+--- source of pass + mirror
             |          |                   |
           [M3]       [M4]                 [MP]  pass PMOS
        diode mir.  mir. out          gate=OTA  drain=VOUT
             |          |                   |
             NA --------+----> OTA ---------+ (CC) --- VOUT
             |          |
           [M1]       [M2]   NMOS input pair  (M1.g=VOUT/FB, M2.g=VREF)
             +----+-----+
                  | TAIL
                [MB1] tail current source (mirrors IBIAS via MB0)
                  |
      VSS --------+--- MB0 diode (gate=drain=IBIAS)

Feedback is unity gain: M1 gate is tied to VOUT.  Output cap COUT (+ESR) sits
on VOUT and forms the dominant pole.
"""

from __future__ import annotations

from .spec import BufferSpec, DeviceSizes, BiasPlan
from .pdk import Pdk, NFET, PFET


def _dev(inst: str, d: str, g: str, s: str, b: str, model: str,
         L: float, W: float, nf: int, m: int) -> str:
    return (f"X{inst} {d} {g} {s} {b} {model} "
            f"L={L} W={W} nf={nf} m={m}")


def buffer_subckt(sz: DeviceSizes) -> str:
    """Return the .subckt definition for the buffer cell.

    Pins: VDD VSS VREF VOUT IBIAS
    IBIAS sinks the external reference current (Iref) to set the OTA tail.
    """
    lines = [
        ".subckt unity_buffer VDD VSS VREF VOUT IBIAS",
        "* ---- bias mirror (NMOS): reference, tail source, output preload ----",
        _dev("MB0", "IBIAS", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_ref),
        _dev("MB1", "TAIL", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_tail),
        # preload sink: a PMOS LDO can only source current, so a guaranteed DC
        # sink at VOUT is needed for the loop to regulate at zero external load
        _dev("MBPRE", "VOUT", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_pre),
        "* ---- NMOS input pair (M1.g=VOUT feedback, M2.g=VREF) ----",
        _dev("M1", "NA", "VOUT", "TAIL", "VSS", NFET,
             sz.li, sz.wi, sz.nfi, sz.mi),
        _dev("M2", "OTA", "VREF", "TAIL", "VSS", NFET,
             sz.li, sz.wi, sz.nfi, sz.mi),
        "* ---- PMOS current-mirror load ----",
        _dev("M3", "NA", "NA", "VDD", "VDD", PFET,
             sz.lm, sz.wm, sz.nfm, sz.mm),
        _dev("M4", "OTA", "NA", "VDD", "VDD", PFET,
             sz.lm, sz.wm, sz.nfm, sz.mm),
        "* ---- PMOS pass device ----",
        _dev("MP", "VOUT", "OTA", "VDD", "VDD", PFET,
             sz.lp, sz.wp, sz.nfp, sz.mp),
    ]
    if sz.cc and sz.cc > 0:
        lines.append(f"CC OTA VOUT {sz.cc:g}")
    lines.append(".ends unity_buffer")
    return "\n".join(lines)


def _header(pdk: Pdk, spec: BufferSpec, title: str) -> list:
    return [
        f"* {title}",
        f'.lib "{pdk.lib_path}" {spec.corner}',
        f".temp {spec.temp}",
        ".param mc_mm_switch=0",
    ]


def _output_cap(spec: BufferSpec) -> list:
    """Output capacitor with optional ESR (series R to ground)."""
    if spec.cout_esr and spec.cout_esr > 0:
        return [
            f"Resr VOUT NESR {spec.cout_esr:g}",
            f"COUT NESR 0 {spec.cout:g}",
        ]
    return [f"COUT VOUT 0 {spec.cout:g}"]


def _instance(spec: BufferSpec, bias: BiasPlan) -> list:
    return [
        "VDD VDD 0 {:g}".format(spec.vdd),
        "VREF VREF 0 {:g}".format(spec.vref),
        # external reference current injected into IBIAS (from a bandgap/Iref)
        "IREF VDD IBIAS {:g}".format(bias.iref),
        "XBUF VDD 0 VREF VOUT IBIAS unity_buffer",
    ]


def _nodeset(spec) -> str:
    """Steer the DC solver to the regulating root (a runaway root also exists)."""
    return (".nodeset v(VOUT)={:g} v(XBUF.OTA)=0.5 "
            "v(XBUF.NA)=0.25 v(XBUF.TAIL)=0.18".format(spec.vout))


def tb_op(pdk, spec, sz, bias, iload: float) -> str:
    """Operating point at a given load current."""
    lines = _header(pdk, spec, f"OP tb, Iload={iload:g}A")
    lines.append(buffer_subckt(sz))
    lines += _instance(spec, bias)
    lines += _output_cap(spec)
    lines.append(f"ILOAD VOUT 0 {iload:g}")
    lines.append(_nodeset(spec))
    lines += [
        ".control",
        "op",
        "wrdata op_vout.txt v(VOUT) v(XBUF.OTA) v(XBUF.NA) v(XBUF.TAIL)",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)


def tb_dc_load(pdk, spec, sz, bias) -> str:
    """DC load sweep 0..iload_max to extract load regulation / Rout."""
    lines = _header(pdk, spec, "DC load sweep")
    lines.append(buffer_subckt(sz))
    lines += _instance(spec, bias)
    lines += _output_cap(spec)
    lines.append("ILOAD VOUT 0 0")
    lines.append(_nodeset(spec))
    step = spec.iload_max / 200.0
    lines += [
        ".control",
        f"dc ILOAD {spec.iload_min:g} {spec.iload_max:g} {step:g}",
        "wrdata dc_load.txt v(VOUT)",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)


def tb_ac_loop(pdk, spec, sz, bias, iload: float) -> str:
    """AC loop-gain testbench using Middlebrook series voltage injection.

    The feedback wire (pass-drain/cap node VOUT -> input-pair gate FB) is broken
    by a 0 V (DC) AC source so the bias is preserved but loop gain can be
    probed.  Loop gain  T = -V(VOUT)/V(FB).
    """
    sz_fb = _subckt_fb(sz)  # variant whose M1 gate is on pin FB
    lines = _header(pdk, spec, f"AC loop gain, Iload={iload:g}A")
    lines.append(sz_fb)
    lines += [
        "VDD VDD 0 {:g}".format(spec.vdd),
        "VREF VREF 0 {:g}".format(spec.vref),
        "IREF VDD IBIAS {:g}".format(bias.iref),
        "XBUF VDD 0 VREF VOUT FB IBIAS unity_buffer_fb",
        # injection: DC short (FB=VOUT) but AC=1 breaks the loop
        "VINJ VOUT FB DC 0 AC 1",
    ]
    lines += _output_cap(spec)
    lines.append(f"ILOAD VOUT 0 {iload:g}")
    lines.append(".nodeset v(VOUT)={:g} v(XBUF.OTA)=0.5 "
                 "v(XBUF.NA)=0.25 v(XBUF.TAIL)=0.18".format(spec.vout))
    lines += [
        ".control",
        "ac dec 40 1 1e9",
        # series voltage injection: loop gain T = -V(VOUT)/V(FB)
        "let loop = -v(VOUT)/v(FB)",
        "wrdata ac_loop.txt vdb(loop) vp(loop)",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)


def _subckt_fb(sz: DeviceSizes) -> str:
    """Buffer variant with the feedback gate exposed as pin FB (for loop AC)."""
    lines = [
        ".subckt unity_buffer_fb VDD VSS VREF VOUT FB IBIAS",
        _dev("MB0", "IBIAS", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_ref),
        _dev("MB1", "TAIL", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_tail),
        _dev("MBPRE", "VOUT", "IBIAS", "VSS", "VSS", NFET,
             sz.lb, sz.wb, sz.nfb, sz.mb_pre),
        _dev("M1", "NA", "FB", "TAIL", "VSS", NFET,
             sz.li, sz.wi, sz.nfi, sz.mi),
        _dev("M2", "OTA", "VREF", "TAIL", "VSS", NFET,
             sz.li, sz.wi, sz.nfi, sz.mi),
        _dev("M3", "NA", "NA", "VDD", "VDD", PFET,
             sz.lm, sz.wm, sz.nfm, sz.mm),
        _dev("M4", "OTA", "NA", "VDD", "VDD", PFET,
             sz.lm, sz.wm, sz.nfm, sz.mm),
        _dev("MP", "VOUT", "OTA", "VDD", "VDD", PFET,
             sz.lp, sz.wp, sz.nfp, sz.mp),
    ]
    if sz.cc and sz.cc > 0:
        lines.append(f"CC OTA VOUT {sz.cc:g}")
    lines.append(".ends unity_buffer_fb")
    return "\n".join(lines)


def tb_tran_step(pdk, spec, sz, bias) -> str:
    """Transient load step iload_min -> iload_max -> iload_min."""
    lines = _header(pdk, spec, "Transient load step")
    lines.append(buffer_subckt(sz))
    lines += _instance(spec, bias)
    lines += _output_cap(spec)
    hi, lo = spec.iload_max, spec.iload_min
    # 200us window: settle, step up at 50us, step down at 150us, 0.5us edges
    lines.append(_nodeset(spec))
    lines += [
        f"ILOAD VOUT 0 PWL(0 {lo:g} 50u {lo:g} 50.5u {hi:g} "
        f"150u {hi:g} 150.5u {lo:g} 200u {lo:g})",
        ".control",
        "tran 0.2u 200u",
        "wrdata tran_step.txt v(VOUT)",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)


def tb_char_pass(pdk, spec, sz) -> str:
    """One pass-cell DC characterization: Id vs gate at the regulated Vsd."""
    lines = _header(pdk, spec, "Pass-cell characterization")
    lines += [
        "VDD VDD 0 {:g}".format(spec.vdd),
        "VOUT VOUT 0 {:g}".format(spec.vout),
        "VG GATE 0 0",
        _dev("MP", "VOUT", "GATE", "VDD", "VDD", PFET,
             sz.lp, sz.wp, sz.nfp, 1),
        ".control",
        "dc VG 0 {:g} 0.02".format(spec.vout),
        "let id = -i(VOUT)",
        "wrdata char_pass.txt id",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)
