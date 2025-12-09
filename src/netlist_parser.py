"""Netlist parsing utilities for SPICE-like amplifier circuits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from utils import parse_value


@dataclass
class Device:
    name: str
    dev_type: str
    nodes: List[str]
    params: Dict[str, float]


@dataclass
class Netlist:
    devices: List[Device]
    nets: Set[str]


class NetlistParser:
    """Parse flattened SPICE netlists into structured objects."""

    def __init__(self) -> None:
        self.supported_devices = {"m": "MOS", "r": "R", "c": "C"}

    def parse_file(self, path: str) -> Netlist:
        devices: List[Device] = []
        nets: Set[str] = set()

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("*", ";")):
                    continue
                if line.lower().startswith(('.include', '.lib', '.control', '.end', '.model')):
                    continue

                prefix = line[0].lower()
                if prefix == "m":
                    device = self._parse_mos(line)
                elif prefix in {"r", "c"}:
                    device = self._parse_passive(line)
                else:
                    continue

                devices.append(device)
                nets.update(device.nodes)

        return Netlist(devices=devices, nets=nets)

    def _parse_mos(self, line: str) -> Device:
        tokens = line.split()
        name = tokens[0]
        d, g, s, b = tokens[1:5]
        model_name = tokens[5].lower()
        params: Dict[str, float] = {}
        for token in tokens[6:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            params[key.upper()] = parse_value(value)

        dev_type = "NMOS" if "n" in model_name else "PMOS"
        return Device(name=name, dev_type=dev_type, nodes=[d, g, s, b], params=params)

    def _parse_passive(self, line: str) -> Device:
        tokens = line.split()
        name = tokens[0]
        n1, n2 = tokens[1:3]
        value = parse_value(tokens[3])
        params: Dict[str, float]
        dev_type: str
        if name.lower().startswith("r"):
            dev_type = "R"
            params = {"R": value}
        else:
            dev_type = "C"
            params = {"C": value}
        return Device(name=name, dev_type=dev_type, nodes=[n1, n2], params=params)


__all__ = ["Device", "Netlist", "NetlistParser"]

