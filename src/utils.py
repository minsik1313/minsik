"""Utility helpers for ngspice pipeline."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict

from config import TARGET_A0_DB, TARGET_ID_A, TARGET_PM_DEG, TARGET_UGBW_HZ


SI_PREFIX = {
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "meg": 1e6,
    "g": 1e9,
}


def parse_value(value: str) -> float:
    """Parse a SPICE numeric literal with simple SI prefixes."""
    token = value.strip().lower()
    for prefix, scale in SI_PREFIX.items():
        if token.endswith(prefix):
            try:
                return float(token[: -len(prefix)]) * scale
            except ValueError:
                continue
    return float(token)


def safe_log10(x: float) -> float:
    """Compute log10 with guarding for non-positive inputs."""
    if x <= 0:
        return 0.0
    return math.log10(x)


def compute_score(spec: Dict[str, float]) -> float:
    """Compute a simple quality score from measured specs."""
    a0 = spec.get("A0_db", 0.0)
    ugbw = spec.get("UGBW_Hz", 0.0)
    pm = spec.get("PM_deg", 0.0)
    current = spec.get("ID_A", 0.0)

    score = 0.0
    score += max(0.0, a0 - TARGET_A0_DB)
    score += 0.001 * max(0.0, ugbw - TARGET_UGBW_HZ)
    score += 0.1 * max(0.0, pm - TARGET_PM_DEG)
    score -= 1000.0 * max(0.0, current - TARGET_ID_A)
    return float(score)


def append_spec_to_csv(csv_path: str | Path, netlist_id: str, spec: Dict[str, float]) -> None:
    """Append a spec row to CSV creating the file when missing."""
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    header = ["netlist_id", "A0_db", "UGBW_Hz", "PM_deg", "ID_A"]
    write_header = not csv_file.exists()

    with csv_file.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        row = {"netlist_id": netlist_id}
        row.update(spec)
        writer.writerow(row)

