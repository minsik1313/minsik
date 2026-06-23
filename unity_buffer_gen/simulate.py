"""ngspice execution and result parsing for the buffer flow.

Each testbench writes a ``wrdata`` text file (whitespace columns, one
``x value`` pair per probed vector).  We run ngspice in batch mode inside a
working directory and parse those files into numpy-free Python lists.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Tuple


class NgspiceError(RuntimeError):
    pass


def ngspice_available() -> bool:
    return shutil.which("ngspice") is not None


def run_deck(deck: str, workdir: str, expect: str) -> str:
    """Write *deck* to workdir, run ngspice -b, return path to *expect* output.

    Raises NgspiceError on failure or if the expected output file is missing.
    """
    os.makedirs(workdir, exist_ok=True)
    deck_path = os.path.join(workdir, "deck.spice")
    with open(deck_path, "w") as fh:
        fh.write(deck)
    proc = subprocess.run(
        ["ngspice", "-b", "deck.spice"],
        cwd=workdir, capture_output=True, text=True, timeout=300,
    )
    out_path = os.path.join(workdir, expect)
    if not os.path.isfile(out_path):
        raise NgspiceError(
            f"ngspice did not produce {expect}.\n"
            f"--- stdout ---\n{proc.stdout[-2000:]}\n"
            f"--- stderr ---\n{proc.stderr[-2000:]}"
        )
    return out_path


def read_columns(path: str) -> List[List[float]]:
    """Parse a wrdata file into a list of numeric rows."""
    rows = []
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue
    return rows


def read_xy(path: str, ycol: int = 1) -> Tuple[List[float], List[float]]:
    """Return (x, y) columns from a wrdata file.  wrdata emits x,y pairs."""
    rows = read_columns(path)
    x = [r[0] for r in rows if len(r) > ycol]
    y = [r[ycol] for r in rows if len(r) > ycol]
    return x, y


@dataclass
class OpResult:
    vout: float
    vota: float
    vna: float
    vtail: float


def parse_op(path: str) -> OpResult:
    rows = read_columns(path)
    if not rows:
        raise NgspiceError("empty op output")
    r = rows[-1]
    # wrdata v(VOUT) v(OTA) v(NA) v(TAIL) -> x,vout,x,vota,x,vna,x,vtail
    # but ngspice collapses repeated x; columns are: x v1 v2 v3 v4 typically.
    # Be tolerant: take pairs.
    vals = r
    # Expected layout from wrdata of 4 vectors at one point: x v1 [x v2 ...]
    # ngspice writes: <x> <y1> <x> <y2> <x> <y3> <x> <y4>
    if len(vals) >= 8:
        return OpResult(vals[1], vals[3], vals[5], vals[7])
    if len(vals) >= 5:
        return OpResult(vals[1], vals[2], vals[3], vals[4])
    raise NgspiceError(f"unexpected op row: {vals}")
