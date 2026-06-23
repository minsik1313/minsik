"""Damped Newton-Raphson with homotopy continuation.

The non-linear algebraic system at each DC point / time-step is solved by
repeatedly assembling the companion-linearised MNA system and solving it.
Robustness (a frequent ngspice pain point) comes from three layers:

  1. per-device limiting (junction voltages clamped inside the device stamp),
  2. gmin stepping  — relax every node-to-ground conductance, then tighten,
  3. source stepping — ramp independent sources from 0 to full value.

Layers 2-3 are classic continuation methods: solve an easy problem and track
the solution to the hard one, which lets us converge circuits where a cold
Newton start diverges.
"""

from __future__ import annotations

import numpy as np

from .linsolve import SparseSolver


class ConvergenceError(RuntimeError):
    pass


def _converged(x_old, x_new, num_nodes, opt):
    reltol, vntol, abstol = opt["reltol"], opt["vntol"], opt["abstol"]
    dv = np.abs(x_new - x_old)
    tol = reltol * np.abs(x_new) + vntol
    tol[num_nodes:] = reltol * np.abs(x_new[num_nodes:]) + abstol
    return bool(np.all(dv <= tol))


def newton_solve(circuit, ctx, x0, solver=None, max_iter=None):
    """Run one Newton solve from initial guess x0. Returns (x, iters)."""
    opt = circuit.options
    max_iter = max_iter or opt["maxiter"]
    solver = solver or SparseSolver()
    x = np.array(x0, dtype=float)
    for it in range(1, max_iter + 1):
        ctx.x = x
        s = circuit.assemble(ctx)
        A = s.matrix()
        x_new = solver.solve(A, s.rhs)
        if not np.all(np.isfinite(x_new)):
            raise ConvergenceError("non-finite iterate")
        if _converged(x, x_new, circuit.num_nodes, opt):
            return x_new, it
        x = x_new
    raise ConvergenceError(f"Newton did not converge in {max_iter} iters")


def solve_with_homotopy(circuit, ctx, x0, solver=None):
    """DC solve with automatic gmin- then source-stepping fallback."""
    solver = solver or SparseSolver()
    # 1) plain Newton
    try:
        return newton_solve(circuit, ctx, x0, solver)
    except ConvergenceError:
        pass

    # 2) gmin stepping: large gmin -> nominal
    nominal = circuit.options["gmin"]
    x = np.array(x0, dtype=float)
    for gmin in np.geomspace(1e-3, nominal, 12):
        ctx.gmin_extra = gmin
        try:
            x, _ = newton_solve(circuit, ctx, x, solver)
        except ConvergenceError:
            break
    else:
        ctx.gmin_extra = 0.0
        return newton_solve(circuit, ctx, x, solver)
    ctx.gmin_extra = 0.0

    # 3) source stepping: ramp sources 0 -> 1
    x = np.array(x0, dtype=float)
    for f in np.linspace(0.0, 1.0, 21):
        ctx.src_factor = f
        x, _ = newton_solve(circuit, ctx, x, solver)
    ctx.src_factor = 1.0
    return x, -1
