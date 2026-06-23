"""Per-solve context passed to every device stamp call."""

from __future__ import annotations

import numpy as np


class StampContext:
    """Carries the current iterate and the numerical knobs a device needs.

    Attributes
    ----------
    x          : current Newton iterate (full MNA vector).
    mode       : 'dc' or 'tran'.
    t, h       : current time and time-step (transient only).
    integrator : active integration strategy (companion models for C/L).
    src_factor : source-stepping homotopy scale in [0, 1].
    gmin_extra : extra diagonal conductance for gmin-stepping homotopy
                 (0 means "use the circuit's nominal gmin").
    """

    def __init__(self, size: int):
        self.x = np.zeros(size)
        self.mode = "dc"
        self.t = 0.0
        self.h = 0.0
        self.h_prev = 0.0
        self.integrator = None
        self.src_factor = 1.0
        self.gmin_extra = 0.0

    def v(self, node: int) -> float:
        """Voltage at an MNA node index (reference node = 0 V)."""
        return 0.0 if node < 0 else self.x[node]
