"""Placement engine: turn a parsed netlist into device coordinates.

Placement rules (the "GUI 배치 규칙"):

1.  Rails.  Nets whose names look like a positive supply (VDD/VCC) are pinned
    to the TOP, ground-like nets (VSS/GND/0) to the BOTTOM.
2.  Voltage layering.  Every device imposes an ordering on its drain/source
    nets: for a PMOS the *source* sits above the *drain*; for an NMOS the
    *drain* sits above the *source*.  A longest-path pass over this DAG gives
    each net a vertical "level" -> the schematic flows VDD(top) -> VSS(bottom).
3.  A device's row is the band between its two power-terminal nets, so series
    (stacked) devices line up vertically.
4.  Columns.  Devices that are series-connected through a signal net share a
    column; differential structures end up side-by-side.  Single devices
    bridging two columns (tail sources, etc.) are centered.
"""

from __future__ import annotations

from dataclasses import dataclass


# ----- net classification -------------------------------------------------

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
    col: int
    row: float        # fractional row (band center)
    flip: bool = False


@dataclass
class Placement:
    devices: list           # list[PlacedDevice]
    net_level: dict         # net -> vertical level (0 = top)
    max_level: int
    n_cols: int
    col_of: dict            # net -> representative column (for routing hints)


def _net_levels(netlist) -> dict:
    """Longest-path layering of nets between VDD (top) and VSS (bottom)."""
    nets = netlist.nets
    # edges: a -> b means a is ABOVE b (closer to VDD)
    succ = {n: set() for n in nets}
    for d in netlist.devices:
        if d.mtype == "pmos":
            hi, lo = d.source, d.drain      # source toward VDD
        else:
            hi, lo = d.drain, d.source      # drain toward VDD
        if hi != lo:
            succ[hi].add(lo)

    # Pin rails.
    level = {}
    for n in nets:
        cls = classify_net(n)
        if cls == "vdd":
            level[n] = 0

    # Longest path from the VDD set downward (relaxation / topological-ish).
    changed = True
    guard = 0
    for n in nets:
        level.setdefault(n, 0)
    while changed and guard < len(nets) + 5:
        changed = False
        guard += 1
        for a in nets:
            for b in succ[a]:
                if level[b] < level[a] + 1:
                    level[b] = level[a] + 1
                    changed = True

    # Push all ground nets to the very bottom so the rail is flat.
    max_lvl = max(level.values()) if level else 0
    gnd_level = max_lvl
    for n in nets:
        if classify_net(n) == "gnd":
            gnd_level = max(gnd_level, level[n])
    for n in nets:
        if classify_net(n) == "gnd":
            level[n] = gnd_level

    return level, max(level.values()) if level else 0


def _assign_columns(netlist, level):
    """Group series-connected devices into shared columns."""
    devices = netlist.devices

    # Union-find over devices that share a signal net on a power terminal.
    parent = {d.name: d.name for d in devices}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # Map signal net -> devices touching it via drain/source.
    net_devs = {}
    for d in devices:
        for term in (d.drain, d.source):
            if classify_net(term) == "signal":
                net_devs.setdefault(term, []).append(d)

    for net, devs in net_devs.items():
        # A node touched by 3+ devices is a shared bus (e.g. the tail node),
        # not a clean series link -> don't merge its devices into one column.
        if len(devs) != 2:
            continue
        # Only chain devices whose levels differ (vertically stacked, not a bus).
        devs_sorted = sorted(devs, key=lambda d: min(level[d.drain], level[d.source]))
        for i in range(len(devs_sorted) - 1):
            a, b = devs_sorted[i], devs_sorted[i + 1]
            la = (level[a.drain], level[a.source])
            lb = (level[b.drain], level[b.source])
            if set(la) & set(lb) and la != lb:
                union(a.name, b.name)

    # Order the resulting groups left to right.
    groups = {}
    for d in devices:
        groups.setdefault(find(d.name), []).append(d)

    # Sort groups: by min level then by name for stability.
    group_keys = sorted(
        groups.keys(),
        key=lambda g: (min(min(level[d.drain], level[d.source]) for d in groups[g]),
                       sorted(d.name for d in groups[g])[0]),
    )

    col_of_group = {}
    multi = [g for g in group_keys if len(groups[g]) > 1]
    singles = [g for g in group_keys if len(groups[g]) == 1]

    # Multi-device (stacked) groups get the primary columns, ordered by name.
    multi.sort(key=lambda g: sorted(d.name for d in groups[g])[0])
    col = 0
    for g in multi:
        col_of_group[g] = col
        col += 1
    n_main = max(col, 1)

    # Single devices get centered among the main columns.
    center = (n_main - 1) / 2.0
    for g in singles:
        col_of_group[g] = center

    n_cols = max([c for c in col_of_group.values()] + [0]) + 1
    return {d.name: col_of_group[find(d.name)] for d in devices}, n_cols


def place(netlist) -> Placement:
    level, max_level = _net_levels(netlist)
    col_map, n_cols = _assign_columns(netlist, level)

    placed = []
    for d in netlist.devices:
        ld, ls = level[d.drain], level[d.source]
        row = (ld + ls) / 2.0
        # Flip so that the gate faces the symmetry axis for the right column.
        col = col_map[d.name]
        flip = col > (n_cols - 1) / 2.0
        placed.append(PlacedDevice(device=d, col=col, row=row, flip=flip))

    # Per-net representative column (median of touching device columns).
    net_cols = {}
    for d in netlist.devices:
        for t in (d.drain, d.gate, d.source, d.bulk):
            net_cols.setdefault(t, []).append(col_map[d.name])
    col_of = {n: sorted(v)[len(v) // 2] for n, v in net_cols.items()}

    return Placement(
        devices=placed,
        net_level=level,
        max_level=max_level,
        n_cols=n_cols,
        col_of=col_of,
    )
