"""Circuit container + Modified Nodal Analysis (MNA) bookkeeping.

Unknown vector x = [ node voltages (1..N-1) ; branch currents of V-sources
and inductors ].  Ground node "0" is the reference and is never stamped.

The assembler builds, on every Newton iteration, a sparse Jacobian J and a
right-hand-side rhs such that solving  J x = rhs  yields the next iterate
(classic "conductance + equivalent current source" companion form used by
SPICE).  Linear devices contribute constant stamps; non-linear devices are
re-linearised about the current iterate; energy-storage devices contribute a
companion model supplied by the active integrator.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix


class Stamper:
    """Accumulates (row, col, value) triplets and an rhs vector.

    Stamps into the reference node (index < 0) are silently dropped, which is
    exactly the MNA reduction of the grounded row/column.
    """

    __slots__ = ("rows", "cols", "vals", "rhs", "n")

    def __init__(self, n: int):
        self.n = n
        self.rows: list[int] = []
        self.cols: list[int] = []
        self.vals: list[float] = []
        self.rhs = np.zeros(n)

    def add(self, i: int, j: int, v: float) -> None:
        if i < 0 or j < 0 or v == 0.0:
            return
        self.rows.append(i)
        self.cols.append(j)
        self.vals.append(v)

    def add_rhs(self, i: int, v: float) -> None:
        if i < 0 or v == 0.0:
            return
        self.rhs[i] += v

    def matrix(self):
        return coo_matrix(
            (self.vals, (self.rows, self.cols)), shape=(self.n, self.n)
        ).tocsc()


class Circuit:
    """Holds nodes + devices and owns the MNA index layout."""

    def __init__(self, title: str = "circuit"):
        self.title = title
        self.devices: list = []
        self._node_index: dict[str, int] = {"0": -1, "gnd": -1}
        self._next_node = 0
        self._branches: dict[str, int] = {}
        self.options = {
            "reltol": 1e-3,
            "abstol": 1e-9,   # current tolerance (A)
            "vntol": 1e-6,    # voltage tolerance (V)
            "gmin": 1e-12,
            "maxiter": 100,
            "trtol": 7.0,     # LTE safety factor (SPICE default)
        }

    # ---- topology -----------------------------------------------------
    def node(self, name: str) -> int:
        name = name.lower()
        if name in self._node_index:
            return self._node_index[name]
        idx = self._next_node
        self._next_node += 1
        self._node_index[name] = idx
        return idx

    def add_branch(self, name: str) -> int:
        """Reserve an extra unknown (a branch current). Returns its index
        relative to the branch block (added after all node unknowns)."""
        if name in self._branches:
            return self._branches[name]
        idx = len(self._branches)
        self._branches[name] = idx
        return idx

    def add(self, device) -> None:
        device.attach(self)
        self.devices.append(device)

    # ---- sizing -------------------------------------------------------
    @property
    def num_nodes(self) -> int:
        return self._next_node

    @property
    def num_branches(self) -> int:
        return len(self._branches)

    @property
    def size(self) -> int:
        return self.num_nodes + self.num_branches

    def branch_global(self, branch_idx: int) -> int:
        """Map a branch index to its global row/col in the MNA system."""
        return self.num_nodes + branch_idx

    def node_names(self) -> dict[int, str]:
        out = {}
        for name, idx in self._node_index.items():
            if idx >= 0 and idx not in out:
                out[idx] = name
        return out

    # ---- assembly -----------------------------------------------------
    def assemble(self, ctx) -> Stamper:
        s = Stamper(self.size)
        gmin = self.options["gmin"]
        # Tiny conductance to ground on every node improves Newton robustness
        # and prevents a singular matrix for floating nodes.
        for i in range(self.num_nodes):
            s.add(i, i, gmin if ctx.gmin_extra == 0 else ctx.gmin_extra)
        for dev in self.devices:
            dev.stamp(s, ctx)
        return s
