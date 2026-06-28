"""Placement engine: turn a parsed netlist into device coordinates.

Placement rules (the "GUI 배치 규칙"):

1.  Rails.  VDD/VCC-like nets are pinned to the TOP, VSS/GND/0 to the BOTTOM.
2.  Voltage layering.  Every device orders its two current-carrying nets
    (PMOS source>drain, NMOS drain>source, diode anode>cathode, resistor by the
    rail it touches).  A longest-path pass gives each net a vertical level so
    the schematic flows VDD(top) -> VSS(bottom).
3.  Row.  A device sits in the band between its two power-net levels, so series
    (stacked) devices line up vertically.
4.  Columns.  Devices series-connected through a signal net share a column;
    nodes touched by 3+ devices are treated as shared buses (not chained).  A
    lone device (e.g. a tail source) is centered between the devices it feeds.
"""

from __future__ import annotations

from dataclasses import dataclass


def classify_net(name: str) -> str:
    u = name.upper()
    if u in ("0", "GND", "VSS", "VSSA", "AGND", "DGND") or u.startswith("VSS"):
        return "gnd"
    if u in ("VDD", "VCC", "VDDA", "VCCA") or u.startswith("VDD") or u.startswith("VCC"):
        return "vdd"
    return "signal"


@dataclass
class PlacedDevice:
    device: object
    col: float
    row: float
    flip: bool = False


@dataclass
class Placement:
    devices: list
    net_level: dict
    max_level: int
    n_cols: int
    col_of: dict


def _net_levels(netlist):
    nets = netlist.nets
    succ = {n: set() for n in nets}

    for d in netlist.devices:
        hi, lo = d.power_terminals()
        if d.kind == "res":
            # no intrinsic direction: orient by whichever rail it touches
            ca, cb = classify_net(hi), classify_net(lo)
            if ca == "vdd" or cb == "gnd":
                pass                      # hi above lo already fine
            elif cb == "vdd" or ca == "gnd":
                hi, lo = lo, hi
            else:
                continue                  # let other devices decide
        if hi != lo:
            succ[hi].add(lo)

    level = {n: 0 for n in nets}
    for n in nets:
        if classify_net(n) == "vdd":
            level[n] = 0

    changed, guard = True, 0
    while changed and guard < len(nets) + 5:
        changed, guard = False, guard + 1
        for a in nets:
            for b in succ[a]:
                if level[b] < level[a] + 1:
                    level[b] = level[a] + 1
                    changed = True

    max_lvl = max(level.values()) if level else 0
    for n in nets:
        if classify_net(n) == "gnd":
            level[n] = max_lvl
    return level, (max(level.values()) if level else 0)


def _power_nets(d):
    return d.power_terminals()


def _assign_columns(netlist, level):
    devices = netlist.devices
    parent = {d.name: d.name for d in devices}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # signal net -> devices touching it on a power terminal
    net_devs = {}
    for d in devices:
        for term in _power_nets(d):
            if classify_net(term) == "signal":
                net_devs.setdefault(term, []).append(d)

    for net, devs in net_devs.items():
        if len(devs) != 2:                # 3+ devices => shared bus, skip
            continue
        devs.sort(key=lambda d: min(level[n] for n in _power_nets(d)))
        a, b = devs
        la = tuple(level[n] for n in _power_nets(a))
        lb = tuple(level[n] for n in _power_nets(b))
        if set(la) & set(lb) and la != lb:
            union(a.name, b.name)

    groups = {}
    for d in devices:
        groups.setdefault(find(d.name), []).append(d)

    multi = [g for g in groups if len(groups[g]) > 1]
    multi.sort(key=lambda g: sorted(d.name for d in groups[g])[0])

    col_of_group = {}
    for i, g in enumerate(multi):
        col_of_group[g] = float(i)
    n_main = max(len(multi), 1)

    col_map = {}
    for d in devices:
        g = find(d.name)
        if g in col_of_group:
            col_map[d.name] = col_of_group[g]

    # place single devices centered between the devices they share a node with
    singles = [g for g in groups if len(groups[g]) == 1]
    for g in singles:
        d = groups[g][0]
        neighbor_cols = []
        for net in _power_nets(d):
            if classify_net(net) != "signal":
                continue
            for other in net_devs.get(net, []):
                if other.name != d.name and other.name in col_map:
                    neighbor_cols.append(col_map[other.name])
        if neighbor_cols:
            col_of_group[g] = sum(neighbor_cols) / len(neighbor_cols)
        else:
            col_of_group[g] = (n_main - 1) / 2.0 + n_main  # park to the right
        col_map[d.name] = col_of_group[g]

    n_cols = max(col_map.values()) + 1 if col_map else 1
    return col_map, n_cols


def place(netlist) -> Placement:
    level, max_level = _net_levels(netlist)
    col_map, n_cols = _assign_columns(netlist, level)

    placed = []
    for d in netlist.devices:
        nets = _power_nets(d)
        lvls = [level[n] for n in nets]
        row = (min(lvls) + max(lvls)) / 2.0
        col = col_map[d.name]
        flip = col > (n_cols - 1) / 2.0
        placed.append(PlacedDevice(device=d, col=col, row=row, flip=flip))

    net_cols = {}
    for d in netlist.devices:
        for t in d.all_nets:
            net_cols.setdefault(t, []).append(col_map[d.name])
    col_of = {n: sorted(v)[len(v) // 2] for n, v in net_cols.items()}

    return Placement(devices=placed, net_level=level, max_level=max_level,
                     n_cols=n_cols, col_of=col_of)
