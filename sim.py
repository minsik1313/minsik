#!/usr/bin/env python3
"""Build + run the MTU cocotb testbenches with Icarus Verilog.

Usage:
    python3 sim.py                  # run every testbench
    python3 sim.py pe               # run a single testbench (pe | systolic_array | mtu_top)
    python3 sim.py --waves          # run everything and dump VCD to results/waves/

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
WAVES = ROOT / "results" / "waves"

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


def _write_vcd_dump_shim(build_dir: Path, toplevel: str, vcd_path: Path) -> Path:
    """A tiny module that dumps every signal under `toplevel` to a real VCD file.

    cocotb's built-in `waves=True` flag asks Icarus for an `.fst` dump, not VCD,
    so we drive $dumpfile/$dumpvars ourselves to guarantee VCD output.
    """
    build_dir.mkdir(parents=True, exist_ok=True)
    shim_path = build_dir / "vcd_dump.sv"
    shim_path.write_text(
        "module vcd_dump_shim();\n"
        "  initial begin\n"
        f'    $dumpfile("{vcd_path}");\n'
        f"    $dumpvars(0, {toplevel});\n"
        "  end\n"
        "endmodule\n"
    )
    return shim_path


def run_one(name: str, dump_waves: bool = False) -> int:
    cfg = CONFIGS[name]
    runner = get_runner("icarus")
    build_dir = ROOT / "sim_build" / name

    sources = [str(p) for p in cfg["sources"]]
    build_args: list[str] = []
    if dump_waves:
        WAVES.mkdir(parents=True, exist_ok=True)
        vcd_path = WAVES / f"{name}.vcd"
        shim = _write_vcd_dump_shim(build_dir, cfg["toplevel"], vcd_path)
        sources.append(str(shim))
        # iverilog elaborates only from -s roots; the shim is a standalone,
        # uninstantiated module so it needs its own root alongside hdl_toplevel.
        build_args = ["-s", "vcd_dump_shim"]

    runner.build(
        sources=sources,
        hdl_toplevel=cfg["toplevel"],
        parameters=cfg["parameters"],
        build_dir=str(build_dir),
        timescale=("1ns", "1ps"),
        build_args=build_args,
        always=True,
    )

    if dump_waves:
        # The runner unconditionally appends a "+fst" (forces FST output,
        # even into our .vcd-named file) or "+none" (suppresses dumping
        # entirely) plusarg depending on `waves`. Neither gives plain VCD, so
        # strip both and let our own $dumpfile/$dumpvars shim run untouched.
        original_test_command = runner._test_command

        def _vcd_test_command():
            return [[arg for arg in cmd if arg not in ("-fst", "-none")]
                    for cmd in original_test_command()]

        runner._test_command = _vcd_test_command

    results_xml = runner.test(
        hdl_toplevel=cfg["toplevel"],
        test_module=cfg["test_module"],
        build_dir=str(build_dir),
        timescale=("1ns", "1ps"),
    )

    _, failed = get_results(results_xml)
    return failed


def main(argv: list[str]) -> int:
    args = argv[1:]
    dump_waves = "--waves" in args
    names = [a for a in args if a != "--waves"] or list(CONFIGS)
    total_failed = 0
    for name in names:
        if name not in CONFIGS:
            print(f"unknown testbench '{name}'; choose from {list(CONFIGS)}")
            return 2
        print(f"\n=== running {name} ===")
        total_failed += run_one(name, dump_waves=dump_waves)
    print(f"\n=== total failed: {total_failed} ===")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
