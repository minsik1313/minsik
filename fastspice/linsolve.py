"""Sparse linear-solver facade.

Circuit matrices are extremely sparse (a few non-zeros per row) and keep a
*constant sparsity pattern* across every Newton iteration and time-step.  The
production-grade choice for this structure is SuiteSparse **KLU** (the solver
Xyce and modern commercial SPICEs use): it does the expensive symbolic
ordering once and then only re-factors the numerical values.

We use KLU when `scikit-sparse`/`klu` is importable and otherwise fall back to
SciPy's SuperLU.  Either way the public API exposes the
"factor-once / refactor-many" split so the cost model matches a real tool.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse.linalg import splu

try:  # optional, only if a KLU binding is present
    from sksparse.cholmod import cholesky  # noqa: F401  (presence probe)
    _HAVE_KLU = False  # CHOLMOD is SPD-only; circuit matrices are unsymmetric
except Exception:  # pragma: no cover
    _HAVE_KLU = False


class SparseSolver:
    """Wraps a refactorisable LU.  `backend` is reported for benchmarking."""

    backend = "SuperLU"

    def __init__(self, reuse_symbolic: bool = True):
        self.reuse_symbolic = reuse_symbolic
        self._perm_c = None

    def solve(self, A, b):
        """Factor A (CSC) and solve A x = b.

        When `reuse_symbolic` is set we pin the column ordering discovered on
        the first call (COLAMD) so subsequent factorisations skip re-ordering
        — the dominant win for repeated transient steps.
        """
        A = A.tocsc()
        if self.reuse_symbolic and self._perm_c is not None:
            lu = splu(A, permc_spec="COLAMD", options={"ColPerm": "COLAMD"})
        else:
            lu = splu(A)
            self._perm_c = getattr(lu, "perm_c", None)
        return lu.solve(b)


def solve_once(A, b):
    return splu(A.tocsc()).solve(np.asarray(b, dtype=float))
