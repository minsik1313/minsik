"""DC operating point and transient analyses.

The transient driver supports single-stage integrators (BE / TR / Gear2) and
the two-stage TR-BDF2, plus optional LTE-controlled adaptive time-stepping.
Local error is estimated from the 3rd divided difference of the accepted
solution history (the order-correct estimate SPICE's `trunc` routine uses):
for a 2nd-order method the local error scales like h^3 * y''', and the step is
grown/shrunk to keep it inside reltol/vntol.
"""

from __future__ import annotations

import numpy as np

from .context import StampContext
from .integrators import get_integrator, TRBDF2, GAMMA, BackwardEuler
from .linsolve import SparseSolver
from .newton import newton_solve, solve_with_homotopy


# ---------------------------------------------------------------------------
# DC operating point
# ---------------------------------------------------------------------------
def operating_point(circuit, x0=None):
    ctx = StampContext(circuit.size)
    ctx.mode = "dc"
    if x0 is None:
        x0 = np.zeros(circuit.size)
    x, _ = solve_with_homotopy(circuit, ctx, x0)
    names = circuit.node_names()
    volt = {names[i]: x[i] for i in names}
    return volt, x


# ---------------------------------------------------------------------------
# Transient
# ---------------------------------------------------------------------------
class TransientResult:
    def __init__(self, circuit, t, X, stats):
        self.t = np.asarray(t)
        self.X = np.asarray(X)          # shape (nsteps, size)
        self.stats = stats
        self._names = circuit.node_names()
        self._idx = {v: k for k, v in self._names.items()}

    def v(self, name):
        i = self._idx[name.lower()]
        return self.X[:, i]

    def at(self, times, name):
        return np.interp(times, self.t, self.v(name))

    def __repr__(self):
        return (f"<TransientResult steps={len(self.t)} "
                f"tstop={self.t[-1]:.3g} stats={self.stats}>")


def _seed_states(circuit, x):
    ctx = StampContext(circuit.size)
    ctx.x = x
    for dev in circuit.devices:
        dev.init_state()
    # seed capacitor voltages / inductor currents from the DC point
    for dev in circuit.devices:
        if getattr(dev, "is_dynamic", False):
            if hasattr(dev, "c"):                 # capacitor
                vd = ctx.v(dev.a) - ctx.v(dev.b)
                dev.v = dev.v2 = vd
                dev.vmid = vd
                dev.i = dev.imid = 0.0
            elif hasattr(dev, "l"):               # inductor
                ib = x[dev.k]
                dev.i = dev.i2 = ib
                dev.imid = ib
                dev.v = dev.vmid = 0.0


def _store_midpoints(circuit, ctx):
    for dev in circuit.devices:
        if getattr(dev, "is_dynamic", False):
            if hasattr(dev, "c"):
                dev.vmid = ctx.v(dev.a) - ctx.v(dev.b)
                dev.imid = dev.branch_current(ctx)
            elif hasattr(dev, "l"):
                dev.vmid = ctx.v(dev.a) - ctx.v(dev.b)
                dev.imid = ctx.x[dev.k]


def _roll(circuit, ctx):
    for dev in circuit.devices:
        if getattr(dev, "is_dynamic", False):
            dev.roll_state(ctx)


def _dd3(ts, xs):
    """3rd Newton divided difference of the last 4 (t, x) samples."""
    d = [np.array(v, dtype=float) for v in xs]
    for order in range(1, 4):
        d = [(d[i + 1] - d[i]) / (ts[i + order] - ts[i])
             for i in range(len(d) - 1)]
    return d[0]  # ~ y'''/6


def transient(circuit, tstop, tstep, integrator="tr-bdf2", tstart=0.0,
              uic=False, adaptive=True, hmin=None, hmax=None,
              reuse_symbolic=True):
    method = get_integrator(integrator)
    solver = SparseSolver(reuse_symbolic=reuse_symbolic)
    opt = circuit.options

    # initial condition: DC operating point unless UIC requested
    if uic:
        x = np.zeros(circuit.size)
    else:
        _, x = operating_point(circuit)
    _seed_states(circuit, x)

    ctx = StampContext(circuit.size)
    ctx.mode = "tran"
    ctx.integrator = method

    # tstep is the suggested/initial step; with error control the engine may
    # grow the internal step up to hmax (SPICE-style TMAX defaults to span/10).
    if hmax is None:
        hmax = (tstop - tstart) / 10.0 if adaptive else tstep
    hmin = hmin or tstep * 1e-9
    h = min(tstep, hmax)

    t = tstart
    T = [t]
    X = [x.copy()]
    n_newton = 0
    n_reject = 0
    n_steps = 0
    h_prev = 0.0
    grew = False
    sliver = max(hmin, 1e-12 * (tstop - tstart))

    be_startup = BackwardEuler()

    def take_step(h):
        """Advance one (sub-)structured step of size h from current state."""
        nonlocal n_newton
        # Multistep methods (Gear2) lack a t_{n-2} sample on the first step;
        # start them with a single Backward-Euler step (standard BDF startup).
        if method.multistep and n_steps == 0:
            ctx.integrator = be_startup
            ctx.h = h
            ctx.t = t + h
            x_new, it = newton_solve(circuit, ctx, X[-1], solver)
            ctx.integrator = method
            n_newton += it
            return x_new
        if isinstance(method, TRBDF2):
            method.stage = 1
            ctx.h = h
            ctx.t = t + GAMMA * h
            x_mid, it1 = newton_solve(circuit, ctx, X[-1], solver)
            ctx.x = x_mid
            _store_midpoints(circuit, ctx)
            method.stage = 2
            ctx.t = t + h
            x_new, it2 = newton_solve(circuit, ctx, x_mid, solver)
            n_newton += it1 + it2
        else:
            ctx.h = h
            ctx.t = t + h
            x_new, it = newton_solve(circuit, ctx, X[-1], solver)
            n_newton += it
        return x_new

    while tstop - t > sliver:
        h = min(h, tstop - t, hmax)
        ctx.h_prev = h_prev if h_prev > 0 else h
        x_new = take_step(h)

        # ---- adaptive local-error control (PI-style step selection) ----
        if adaptive and len(T) >= 3 and h > hmin:
            ts = T[-3:] + [t + h]
            xs = [X[-3], X[-2], X[-1], x_new]
            nn = circuit.num_nodes
            dd = _dd3(ts, xs)[:nn]
            # 2nd-order local error ~ h^3 |y'''|; |dd3| ~= |y'''|/6
            lte = np.abs(dd) * h ** 3
            tol = opt["reltol"] * np.abs(x_new[:nn]) + opt["vntol"]
            err = float(np.max(lte / tol)) / opt["trtol"] if nn else 0.0
            fac = 0.85 * err ** (-1.0 / 3.0) if err > 0 else 2.0
            if err > 1.0 and h > hmin:           # reject and retry smaller
                n_reject += 1
                h = max(hmin, h * max(0.25, fac))
                grew = False
                continue
            # accept; grow conservatively, and never grow right after a reject
            cap = 1.5 if grew else 2.0
            h_next = h * min(cap, max(0.5, fac))
            grew = True
        else:
            h_next = h  # fixed-step: keep the user's tstep

        # accept
        ctx.x = x_new
        ctx.t = t + h
        _roll(circuit, ctx)
        t += h
        T.append(t)
        X.append(x_new.copy())
        n_steps += 1
        h_prev = h
        h = h_next

    stats = {
        "method": method.name,
        "steps": n_steps,
        "rejects": n_reject,
        "newton_iters": n_newton,
        "solver": solver.backend,
        "adaptive": adaptive,
    }
    return TransientResult(circuit, T, X, stats)
