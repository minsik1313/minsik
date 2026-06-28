"""SPICE netlist parser (focused on MOSFET-level analog schematics)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Device:
    """A single MOSFET instance."""

    name: str
    drain: str
    gate: str
    source: str
    bulk: str
    model: str
    mtype: str = "nmos"          # resolved from .model lines: 'nmos' | 'pmos'
    params: dict = field(default_factory=dict)

    @property
    def terminals(self) -> dict:
        return {"D": self.drain, "G": self.gate, "S": self.source, "B": self.bulk}


@dataclass
class Netlist:
    devices: list = field(default_factory=list)
    models: dict = field(default_factory=dict)   # model name -> type
    globals: set = field(default_factory=set)

    @property
    def nets(self) -> set:
        n = set()
        for d in self.devices:
            n.update([d.drain, d.gate, d.source, d.bulk])
        return n


def _parse_params(tokens: list) -> dict:
    params = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            params[k.strip().upper()] = v.strip()
    return params


def parse(text: str) -> Netlist:
    """Parse SPICE text into a :class:`Netlist`.

    Continuation lines (starting with '+') are joined; comments ('*') and
    blank lines are skipped.
    """
    nl = Netlist()
    raw_lines = []

    # Join continuation lines first.
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.startswith("+") and raw_lines:
            raw_lines[-1] += " " + stripped[1:].strip()
        else:
            raw_lines.append(stripped)

    for line in raw_lines:
        tokens = line.split()
        head = tokens[0].lower()

        if head == ".model" and len(tokens) >= 3:
            nl.models[tokens[1]] = tokens[2].lower()

        elif head == ".global":
            nl.globals.update(tokens[1:])

        elif head in (".end", ".ends"):
            continue

        elif head.startswith("m") and len(tokens) >= 6:
            # M<name> D G S B model [params]
            name, d, g, s, b, model = tokens[:6]
            dev = Device(
                name=name,
                drain=d,
                gate=g,
                source=s,
                bulk=b,
                model=model,
                params=_parse_params(tokens[6:]),
            )
            nl.devices.append(dev)

    # Resolve transistor type from model table (fallback: guess by model name).
    for dev in nl.devices:
        mtype = nl.models.get(dev.model)
        if mtype is None:
            mtype = "pmos" if "p" in dev.model.lower() else "nmos"
        dev.mtype = "pmos" if mtype.startswith("p") else "nmos"

    return nl


def parse_file(path: str) -> Netlist:
    with open(path, "r", encoding="utf-8") as fh:
        return parse(fh.read())
