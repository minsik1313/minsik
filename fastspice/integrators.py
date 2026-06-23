"""Time-integration strategies (companion models for C and L).

Each integrator turns the constitutive relation of an energy-storage element
into an instantaneous "conductance + source" companion so the non-linear
solver only ever sees an algebraic system:

    capacitor :  i  = g  * v + ieq
    inductor  :  v  = req * i + veq

`ctx.h` carries the (sub-)step size in use.  Multi-stage methods (TR-BDF2)
read `self.stage` to select the active formula; the transient driver in
analyses.py orchestrates the stages and history roll.
"""

from __future__ import annotations

import math

GAMMA = 2.0 - math.sqrt(2.0)  # TR-BDF2 splitting point (L-stable choice)


class Integrator:
    name = "base"
    order = 1
    multistep = False
    stages = 1

    def cap_companion(self, C, dev, ctx):  # pragma: no cover - interface
        raise NotImplementedError

    def ind_companion(self, L, dev, ctx):  # pragma: no cover - interface
        raise NotImplementedError


class BackwardEuler(Integrator):
    name = "BE"
    order = 1

    def cap_companion(self, C, dev, ctx):
        g = C / ctx.h
        return g, -g * dev.v

    def ind_companion(self, L, dev, ctx):
        req = L / ctx.h
        return req, -req * dev.i


class Trapezoidal(Integrator):
    name = "TR"
    order = 2

    def cap_companion(self, C, dev, ctx):
        g = 2.0 * C / ctx.h
        return g, -g * dev.v - dev.i

    def ind_companion(self, L, dev, ctx):
        req = 2.0 * L / ctx.h
        return req, -req * dev.i - dev.v


class Gear2(Integrator):
    """2nd-order BDF, variable step.  Stiffly stable, no trapezoidal ringing.

    Uses the *variable-step* BDF2 derivative so that non-uniform steps
    (adaptive control, or the final partial step to land on tstop) stay
    2nd-order accurate instead of corrupting the result:

        y'_n = [ (1+2r)/(1+r) y_n - (1+r) y_{n-1} + r^2/(1+r) y_{n-2} ] / h_n
        with r = h_n / h_{n-1}   (reduces to (3,-4,1)/(2h) when r = 1).
    """

    name = "Gear2"
    order = 2
    multistep = True

    @staticmethod
    def _r(ctx):
        hp = ctx.h_prev if ctx.h_prev > 0 else ctx.h
        return ctx.h / hp

    def cap_companion(self, C, dev, ctx):
        h, r = ctx.h, self._r(ctx)
        g = C / h * (1.0 + 2.0 * r) / (1.0 + r)
        ieq = C / h * (-(1.0 + r) * dev.v + r * r / (1.0 + r) * dev.v2)
        return g, ieq

    def ind_companion(self, L, dev, ctx):
        h, r = ctx.h, self._r(ctx)
        req = L / h * (1.0 + 2.0 * r) / (1.0 + r)
        veq = L / h * (-(1.0 + r) * dev.i + r * r / (1.0 + r) * dev.i2)
        return req, veq


class TRBDF2(Integrator):
    """Composite one-step TR-BDF2 (Bank et al. 1985).

    Stage 1: trapezoidal across [t, t+gamma*h]  -> midpoint state.
    Stage 2: BDF2 across the unequal points (t, t+gamma*h, t+h).
    L-stable, 2nd-order, and — unlike pure trapezoidal — strongly damps the
    numerical ringing that plagues SPICE's default integrator, while staying
    far more accurate than Backward Euler.
    """

    name = "TR-BDF2"
    order = 2
    stages = 2

    def __init__(self):
        self.stage = 1
        self.r = (1.0 - GAMMA) / GAMMA  # = 1/sqrt(2) for the L-stable choice

    # -- capacitor ----------------------------------------------------
    def cap_companion(self, C, dev, ctx):
        h = ctx.h
        if self.stage == 1:
            d1 = GAMMA * h
            g = 2.0 * C / d1
            return g, -g * dev.v - dev.i
        # stage 2 : BDF2 on (t, t+gamma h, t+h)
        h2 = (1.0 - GAMMA) * h
        r = self.r
        g = C / h2 * (1.0 + 2.0 * r) / (1.0 + r)
        ieq = C / h2 * (-(1.0 + r) * dev.vmid + r * r / (1.0 + r) * dev.v)
        return g, ieq

    # -- inductor -----------------------------------------------------
    def ind_companion(self, L, dev, ctx):
        h = ctx.h
        if self.stage == 1:
            d1 = GAMMA * h
            req = 2.0 * L / d1
            return req, -req * dev.i - dev.v
        h2 = (1.0 - GAMMA) * h
        r = self.r
        req = L / h2 * (1.0 + 2.0 * r) / (1.0 + r)
        veq = L / h2 * (-(1.0 + r) * dev.imid + r * r / (1.0 + r) * dev.i)
        return req, veq


_BY_NAME = {
    "be": BackwardEuler,
    "backward_euler": BackwardEuler,
    "tr": Trapezoidal,
    "trap": Trapezoidal,
    "trapezoidal": Trapezoidal,
    "gear": Gear2,
    "gear2": Gear2,
    "trbdf2": TRBDF2,
    "tr-bdf2": TRBDF2,
}


def get_integrator(name):
    if isinstance(name, Integrator):
        return name
    cls = _BY_NAME.get(str(name).lower())
    if cls is None:
        raise ValueError(f"unknown integrator '{name}'")
    return cls()
