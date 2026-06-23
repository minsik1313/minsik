"""A small SPICE netlist parser (subset sufficient for the benchmarks).

Supported cards:
    R/C/L  n1 n2 value
    V/I    n1 n2 [DC] value | PULSE(...) | SIN(...)
    D      n1 n2 modelname
    .model name D (IS=.. N=.. )
    .tran  tstep tstop [tstart] [UIC]
    .end / comments (* or ;)
Engineering suffixes (f p n u m k meg g t) are understood.
"""

from __future__ import annotations

import re

from .circuit import Circuit
from .devices import (Resistor, Capacitor, Inductor, VoltageSource,
                      CurrentSource, Diode, DCValue, Pulse, Sine)

_SUFFIX = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
    "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "t": 1e12,
}


def _num(tok: str) -> float:
    tok = tok.strip().lower()
    m = re.match(r"^([+-]?\d*\.?\d+(?:e[+-]?\d+)?)([a-zµ]*)", tok)
    if not m:
        return float(tok)
    val = float(m.group(1))
    suf = m.group(2)
    if suf.startswith("meg"):
        return val * 1e6
    if suf and suf[0] in _SUFFIX:
        return val * _SUFFIX[suf[0]]
    return val


def _args(spec: str):
    inside = spec[spec.find("(") + 1: spec.rfind(")")]
    return [_num(t) for t in re.split(r"[,\s]+", inside.strip()) if t]


def parse_netlist(text: str):
    lines = text.splitlines()
    title = lines[0].strip() if lines else "circuit"
    c = Circuit(title)
    models = {}
    tran = None

    # gather .model first
    body = lines[1:]
    for raw in body:
        line = raw.strip()
        if line.lower().startswith(".model"):
            toks = line.split()
            name = toks[1].lower()
            params = {}
            for kv in re.findall(r"(\w+)\s*=\s*([0-9.eE+\-a-zµ]+)", line):
                params[kv[0].lower()] = _num(kv[1])
            models[name] = params

    for raw in body:
        line = raw.strip()
        if not line or line[0] in "*;":
            continue
        low = line.lower()
        if low.startswith(".model"):
            continue
        if low.startswith(".tran"):
            toks = line.split()
            tstep = _num(toks[1])
            tstop = _num(toks[2])
            tstart = _num(toks[3]) if len(toks) > 3 and not toks[3].lower().startswith("uic") else 0.0
            uic = low.rstrip().endswith("uic")
            tran = dict(tstep=tstep, tstop=tstop, tstart=tstart, uic=uic)
            continue
        if low.startswith(".end") or line.startswith("."):
            continue

        toks = line.split()
        name, n1, n2 = toks[0], toks[1], toks[2]
        kind = name[0].upper()
        if kind == "R":
            c.add(Resistor(name, n1, n2, _num(toks[3])))
        elif kind == "C":
            c.add(Capacitor(name, n1, n2, _num(toks[3])))
        elif kind == "L":
            c.add(Inductor(name, n1, n2, _num(toks[3])))
        elif kind in ("V", "I"):
            wave = _parse_source(toks[3:])
            dev = VoltageSource if kind == "V" else CurrentSource
            c.add(dev(name, n1, n2, wave))
        elif kind == "D":
            mp = models.get(toks[3].lower(), {})
            c.add(Diode(name, n1, n2,
                        is_=mp.get("is", 1e-14),
                        n=mp.get("n", 1.0)))
        else:
            raise ValueError(f"unsupported device card: {line}")
    return c, tran


def _parse_source(rest):
    spec = " ".join(rest)
    low = spec.lower()
    if low.startswith("pulse"):
        return Pulse(*_args(spec))
    if low.startswith("sin"):
        return Sine(*_args(spec))
    # DC [value] form
    toks = spec.replace("dc", " ").split()
    return DCValue(_num(toks[0]))


def parse_file(path: str):
    with open(path) as f:
        return parse_netlist(f.read())
