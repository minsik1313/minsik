#!/usr/bin/env python3
"""Build + run the MTU cocotb testbenches with Icarus Verilog.

Usage:
    python3 sim.py            # run every testbench
    python3 sim.py pe         # run a single testbench (pe | systolic_array | mtu_top)

Exit code is non-zero if any test fails, so this doubles as the CI entry point.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cocotb_tools.runner import get_runner, get_results

ROOT = Path(__file__).parent.resolve()
RTL = ROOT / "rtl"
TB = ROOT / "tb"
MODEL = ROOT / "model"

# The cocotb runner derives the sim's PYTHONPATH from this process's sys.path,
# so make the testbench + golden-model packages importable here.
for _p in (TB, MODEL, ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Per-DUT: RTL sources, cocotb test module, top module, build parameters.
CONFIGS = {
    "pe": {
        "sources": [RTL / "pe" / "pe.sv"],
        "test_module": "test_pe",
        "toplevel": "pe",
        "parameters": {},
    },
    "systolic_array": {
        "sources": [RTL / "pe" / "pe.sv", RTL / "mxu" / "systolic_array.sv"],
        "test_module": "test_systolic_array",
        "toplevel": "systolic_array",
        "parameters": {"ROWS": 4, "COLS": 4},
    },
    "mtu_top": {
        "sources": [RTL / "pe" / "pe.sv", RTL / "mxu" / "systolic_array.sv",
                    RTL / "mtu_top.sv"],
        "test_module": "test_mtu_top",
        "toplevel": "mtu_top",
        "parameters": {"ARRAY_ROWS": 8, "ARRAY_COLS": 8},
    },
}


def run_one(name: str) -> int:
    cfg = CONFIGS[name]
    runner = get_runner("icarus")
    build_dir = ROOT / "sim_build" / name

    runner.build(
        sources=[str(p) for p in cfg["sources"]],
        hdl_toplevel=cfg["toplevel"],
        parameters=cfg["parameters"],
        build_dir=str(build_dir),
        timescale=("1ns", "1ps"),
        always=True,
    )

    results_xml = runner.test(
        hdl_toplevel=cfg["toplevel"],
        test_module=cfg["test_module"],
        build_dir=str(build_dir),
        timescale=("1ns", "1ps"),
    )

    _, failed = get_results(results_xml)
    return failed


def main(argv: list[str]) -> int:
    names = argv[1:] if len(argv) > 1 else list(CONFIGS)
    total_failed = 0
    for name in names:
        if name not in CONFIGS:
            print(f"unknown testbench '{name}'; choose from {list(CONFIGS)}")
            return 2
        print(f"\n=== running {name} ===")
        total_failed += run_one(name)
    print(f"\n=== total failed: {total_failed} ===")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
