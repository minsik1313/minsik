"""SPICE netlist parser (MOSFET / resistor / diode level schematics)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Device:
    """A circuit element.

    ``kind`` is one of 'mos', 'res', 'diode'.  ``nodes`` maps a role name to a
    net:
        mos   -> {'D','G','S','B'}
        res   -> {'A','B'}
        diode -> {'A','K'}   (anode / cathode)
    """

    kind: str
    name: str
    nodes: dict
    model: str = ""
    mtype: str = ""                 # 'nmos'|'pmos' for mos
    value: str = ""                 # e.g. resistor value
    params: dict = field(default_factory=dict)

    # --- convenience accessors ---
    @property
    def drain(self):  return self.nodes.get("D")
    @property
    def gate(self):   return self.nodes.get("G")
    @property
    def source(self): return self.nodes.get("S")
    @property
    def bulk(self):   return self.nodes.get("B")

    def power_terminals(self):
        """Return the two current-carrying nets (hi-preference, lo-preference)."""
        if self.kind == "mos":
            if self.mtype == "pmos":
                return self.nodes["S"], self.nodes["D"]   # source toward VDD
            return self.nodes["D"], self.nodes["S"]        # drain toward VDD
        if self.kind == "diode":
            return self.nodes["A"], self.nodes["K"]        # anode toward VDD
        if self.kind == "res":
            return self.nodes["A"], self.nodes["B"]
        return None

    @property
    def all_nets(self):
        return list(self.nodes.values())


@dataclass
class Netlist:
    devices: list = field(default_factory=list)
    models: dict = field(default_factory=dict)
    globals: set = field(default_factory=set)

    @property
    def nets(self) -> set:
        n = set()
        for d in self.devices:
            n.update(d.all_nets)
        return n


def _parse_params(tokens: list) -> dict:
    params = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            params[k.strip().upper()] = v.strip()
    return params


def parse(text: str) -> Netlist:
    nl = Netlist()
    raw_lines = []

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("*"):
            continue
        if s.startswith("+") and raw_lines:
            raw_lines[-1] += " " + s[1:].strip()
        else:
            raw_lines.append(s)

    for line in raw_lines:
        tok = line.split()
        head = tok[0].lower()

        if head == ".model" and len(tok) >= 3:
            nl.models[tok[1]] = tok[2].lower()

        elif head == ".global":
            nl.globals.update(tok[1:])

        elif head in (".end", ".ends"):
            continue

        elif head.startswith("m") and len(tok) >= 6:
            name, d, g, s, b, model = tok[:6]
            nl.devices.append(Device(
                kind="mos", name=name,
                nodes={"D": d, "G": g, "S": s, "B": b},
                model=model, params=_parse_params(tok[6:]),
            ))

        elif head.startswith("r") and len(tok) >= 3:
            name, n1, n2 = tok[:3]
            value = tok[3] if len(tok) > 3 and "=" not in tok[3] else ""
            nl.devices.append(Device(
                kind="res", name=name,
                nodes={"A": n1, "B": n2}, value=value,
                params=_parse_params(tok[3:]),
            ))

        elif head.startswith("d") and len(tok) >= 3:
            name, a, k = tok[:3]
            model = tok[3] if len(tok) > 3 and "=" not in tok[3] else ""
            nl.devices.append(Device(
                kind="diode", name=name,
                nodes={"A": a, "K": k}, model=model,
                params=_parse_params(tok[3:]),
            ))

    # resolve mos type
    for d in nl.devices:
        if d.kind != "mos":
            continue
        mt = nl.models.get(d.model)
        if mt is None:
            mt = "pmos" if "p" in d.model.lower() else "nmos"
        d.mtype = "pmos" if mt.startswith("p") else "nmos"

    return nl


def parse_file(path: str) -> Netlist:
    with open(path, "r", encoding="utf-8") as fh:
        return parse(fh.read())
