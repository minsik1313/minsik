"""Lightweight ngspice wrapper for AC/spec extraction."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from utils import append_spec_to_csv


MEASURE_KEYS = ["A0_db", "UGBW_Hz", "PM_deg", "ID_A"]


class NgspiceRunner:
    """Execute ngspice analyses and parse simple measures."""

    def __init__(self, ngspice_cmd: str = "ngspice") -> None:
        self.ngspice_cmd = ngspice_cmd

    def run_ac_analysis(self, netlist_path: str) -> Dict[str, float]:
        """Run AC analysis on a given netlist and return measured specs."""
        spec: Dict[str, float] = {k: 0.0 for k in MEASURE_KEYS}
        netlist_text = Path(netlist_path).read_text(encoding="utf-8")
        control_block = self._control_block()

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cir") as tmp:
            tmp.write(netlist_text)
            if not netlist_text.strip().lower().endswith(".end"):
                tmp.write("\n")
            tmp.write(control_block)
            tmp_path = tmp.name

        cmd = [self.ngspice_cmd, "-b", "-o", tmp_path + ".log", tmp_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            log_text = Path(tmp_path + ".log").read_text(encoding="utf-8", errors="ignore")
            spec.update(self._parse_measures(log_text))
        except FileNotFoundError:
            # ngspice missing: keep default zeros
            pass
        except subprocess.CalledProcessError:
            # failed run: return zeros
            pass
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                Path(tmp_path + ".log").unlink(missing_ok=True)
            except OSError:
                pass

        return spec

    def _control_block(self) -> str:
        control_lines = [
            ".control",
            "set filetype=ascii",
            "op",
            "ac dec 100 10 1e9",
            "meas ac A0_db FIND vdb(VOUT) AT=10",
            "meas ac UGBW_Hz WHEN vdb(VOUT)=0",
            "meas ac PM_deg FIND phase(VOUT) WHEN vdb(VOUT)=0",
            "meas op ID_A PARAM -I(VDD)",
            "quit",
            ".endc",
        ]
        return "\n".join(control_lines) + "\n"

    def _parse_measures(self, text: str) -> Dict[str, float]:
        results: Dict[str, float] = {}
        for key in MEASURE_KEYS:
            match = re.search(rf"{key}\s*=\s*([-+eE0-9\.]+)", text)
            if match:
                try:
                    results[key] = float(match.group(1))
                except ValueError:
                    continue
        return results


__all__ = ["NgspiceRunner", "append_spec_to_csv"]

