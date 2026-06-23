"""FastSpice — a compact, modern SPICE-class circuit simulator.

Goals over a classic ngspice flow:
  * Accuracy  : TR-BDF2 (L-stable, 2nd order) integration that removes the
                trapezoidal ringing artefact, plus LTE-controlled adaptive
                time-stepping and a robust damped Newton with gmin/source
                homotopy continuation.
  * Speed     : sparse KLU/SuperLU factorisation with cached symbolic
                ordering, fewer time-steps via error control, and an
                optional parallel device-evaluation path.

The package is intentionally small and readable so each numerical choice can
be inspected and benchmarked against ngspice / analytic references.
"""

from .circuit import Circuit
from .parser import parse_netlist, parse_file
from .analyses import operating_point, transient, TransientResult
from .integrators import BackwardEuler, Trapezoidal, Gear2, TRBDF2

__all__ = [
    "Circuit",
    "parse_netlist",
    "parse_file",
    "operating_point",
    "transient",
    "TransientResult",
    "BackwardEuler",
    "Trapezoidal",
    "Gear2",
    "TRBDF2",
]

__version__ = "0.1.0"
