"""Device models and their MNA stamps.

Every device implements:
    attach(circuit)  -> resolve node indices / reserve branch unknowns
    stamp(stamper, ctx)
Energy-storage and stateful devices additionally implement:
    init_state(), roll_state(ctx), compute_branch(ctx)

Companion models for C and L are delegated to the active integrator
(ctx.integrator) so that the same device works under BE / TR / Gear2 / TR-BDF2
without modification.
"""

from __future__ import annotations

import math
import numpy as np


# ---------------------------------------------------------------------------
# Source waveforms
# ---------------------------------------------------------------------------
class Waveform:
    def value(self, t: float) -> float:  # pragma: no cover - interface
        raise NotImplementedError

    @property
    def dc(self) -> float:
        return self.value(0.0)


class DCValue(Waveform):
    def __init__(self, v):
        self.v = float(v)

    def value(self, t):
        return self.v


class Pulse(Waveform):
    """PULSE(v1 v2 td tr tf pw per)."""

    def __init__(self, v1, v2, td=0.0, tr=1e-9, tf=1e-9, pw=1e-3, per=2e-3):
        self.v1, self.v2 = float(v1), float(v2)
        self.td, self.tr, self.tf = float(td), float(tr), float(tf)
        self.pw, self.per = float(pw), float(per)

    @property
    def dc(self):
        return self.v1

    def value(self, t):
        if t < self.td:
            return self.v1
        tt = (t - self.td) % self.per if self.per > 0 else (t - self.td)
        if tt < self.tr:
            return self.v1 + (self.v2 - self.v1) * (tt / self.tr)
        tt -= self.tr
        if tt < self.pw:
            return self.v2
        tt -= self.pw
        if tt < self.tf:
            return self.v2 + (self.v1 - self.v2) * (tt / self.tf)
        return self.v1


class Sine(Waveform):
    """SIN(vo va freq td theta)."""

    def __init__(self, vo, va, freq, td=0.0, theta=0.0):
        self.vo, self.va, self.freq = float(vo), float(va), float(freq)
        self.td, self.theta = float(td), float(theta)

    @property
    def dc(self):
        return self.vo

    def value(self, t):
        if t < self.td:
            return self.vo
        tt = t - self.td
        damp = math.exp(-self.theta * tt) if self.theta else 1.0
        return self.vo + self.va * damp * math.sin(2 * math.pi * self.freq * tt)


# ---------------------------------------------------------------------------
# Base device
# ---------------------------------------------------------------------------
class Device:
    is_dynamic = False

    def __init__(self, name):
        self.name = name

    def attach(self, circuit):  # pragma: no cover - interface
        raise NotImplementedError

    def stamp(self, s, ctx):  # pragma: no cover - interface
        raise NotImplementedError

    def init_state(self):
        pass

    def roll_state(self, ctx):
        pass


# ---------------------------------------------------------------------------
# Linear two-terminal devices
# ---------------------------------------------------------------------------
class Resistor(Device):
    def __init__(self, name, n1, n2, r):
        super().__init__(name)
        self.n1, self.n2, self.r = n1, n2, float(r)

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)
        self.g = 1.0 / self.r

    def stamp(self, s, ctx):
        g = self.g
        s.add(self.a, self.a, g)
        s.add(self.b, self.b, g)
        s.add(self.a, self.b, -g)
        s.add(self.b, self.a, -g)


class Capacitor(Device):
    is_dynamic = True

    def __init__(self, name, n1, n2, c, ic=0.0):
        super().__init__(name)
        self.n1, self.n2, self.c, self.ic = n1, n2, float(c), float(ic)

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)

    def init_state(self):
        # history: previous voltage(s) and current
        self.v = self.ic
        self.v2 = self.ic
        self.i = 0.0
        self.vmid = self.ic
        self.imid = 0.0

    def stamp(self, s, ctx):
        if ctx.mode == "dc":
            return  # open circuit at DC
        g, ieq = ctx.integrator.cap_companion(self.c, self, ctx)
        self._g, self._ieq = g, ieq
        s.add(self.a, self.a, g)
        s.add(self.b, self.b, g)
        s.add(self.a, self.b, -g)
        s.add(self.b, self.a, -g)
        # i flows a->b ;  i = g*(va-vb) + ieq
        s.add_rhs(self.a, -ieq)
        s.add_rhs(self.b, ieq)

    def branch_current(self, ctx):
        vd = ctx.v(self.a) - ctx.v(self.b)
        return self._g * vd + self._ieq

    def roll_state(self, ctx):
        vd = ctx.v(self.a) - ctx.v(self.b)
        self.i = self.branch_current(ctx)
        self.v2 = self.v
        self.v = vd


class Inductor(Device):
    is_dynamic = True

    def __init__(self, name, n1, n2, l, ic=0.0):
        super().__init__(name)
        self.n1, self.n2, self.l, self.ic = n1, n2, float(l), float(ic)

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)
        self.br = c.add_branch("L:" + self.name)
        self.circuit = c

    @property
    def k(self):
        return self.circuit.branch_global(self.br)

    def init_state(self):
        self.i = self.ic
        self.i2 = self.ic
        self.v = 0.0
        self.imid = self.ic
        self.vmid = 0.0

    def stamp(self, s, ctx):
        k = self.k
        # KCL: branch current leaves a, enters b
        s.add(self.a, k, 1.0)
        s.add(self.b, k, -1.0)
        if ctx.mode == "dc":
            # short circuit: v_a - v_b = 0
            s.add(k, self.a, 1.0)
            s.add(k, self.b, -1.0)
            return
        req, veq = ctx.integrator.ind_companion(self.l, self, ctx)
        self._req, self._veq = req, veq
        # branch equation: (va - vb) - req*i - veq = 0
        s.add(k, self.a, 1.0)
        s.add(k, self.b, -1.0)
        s.add(k, k, -req)
        s.add_rhs(k, veq)

    def branch_current(self, ctx):
        return ctx.x[self.k]

    def roll_state(self, ctx):
        self.i2 = self.i
        self.i = ctx.x[self.k]
        self.v = ctx.v(self.a) - ctx.v(self.b)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
class VoltageSource(Device):
    def __init__(self, name, n1, n2, wave):
        super().__init__(name)
        self.n1, self.n2 = n1, n2
        self.wave = wave if isinstance(wave, Waveform) else DCValue(wave)

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)
        self.br = c.add_branch("V:" + self.name)
        self.circuit = c

    @property
    def k(self):
        return self.circuit.branch_global(self.br)

    def stamp(self, s, ctx):
        k = self.k
        s.add(self.a, k, 1.0)
        s.add(self.b, k, -1.0)
        s.add(k, self.a, 1.0)
        s.add(k, self.b, -1.0)
        val = self.wave.dc if ctx.mode == "dc" else self.wave.value(ctx.t)
        s.add_rhs(k, val * ctx.src_factor)

    def branch_current(self, ctx):
        return ctx.x[self.k]


class CurrentSource(Device):
    def __init__(self, name, n1, n2, wave):
        super().__init__(name)
        self.n1, self.n2 = n1, n2
        self.wave = wave if isinstance(wave, Waveform) else DCValue(wave)

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)

    def stamp(self, s, ctx):
        val = (self.wave.dc if ctx.mode == "dc" else self.wave.value(ctx.t))
        val *= ctx.src_factor
        # current flows from n1 to n2 internally -> leaves a, enters b
        s.add_rhs(self.a, -val)
        s.add_rhs(self.b, val)


# ---------------------------------------------------------------------------
# Non-linear device: junction diode (with voltage limiting)
# ---------------------------------------------------------------------------
class Diode(Device):
    def __init__(self, name, n1, n2, is_=1e-14, n=1.0, vt=0.02585, gmin=1e-12):
        super().__init__(name)
        self.n1, self.n2 = n1, n2
        self.Is, self.n, self.Vt, self.gmin = float(is_), float(n), float(vt), float(gmin)
        self.vd_old = 0.0

    def attach(self, c):
        self.a = c.node(self.n1)
        self.b = c.node(self.n2)

    def init_state(self):
        self.vd_old = 0.0

    @staticmethod
    def _limit(vnew, vold, vt, vcrit):
        """SPICE pn-junction limiting to aid Newton convergence."""
        if vnew > vcrit and abs(vnew - vold) > 2 * vt:
            if vold > 0:
                arg = 1 + (vnew - vold) / vt
                vnew = vold + vt * math.log(arg) if arg > 0 else vcrit
            else:
                vnew = vt * math.log(vnew / vt) if vnew / vt > 0 else vcrit
        return vnew

    def stamp(self, s, ctx):
        vd = ctx.v(self.a) - ctx.v(self.b)
        nvt = self.n * self.Vt
        vcrit = nvt * math.log(nvt / (math.sqrt(2.0) * self.Is))
        vd = self._limit(vd, self.vd_old, nvt, vcrit)
        self.vd_old = vd
        evd = math.exp(min(vd / nvt, 40.0))
        Id = self.Is * (evd - 1.0) + self.gmin * vd
        gd = self.Is / nvt * evd + self.gmin
        Ieq = Id - gd * vd  # Newton companion current
        s.add(self.a, self.a, gd)
        s.add(self.b, self.b, gd)
        s.add(self.a, self.b, -gd)
        s.add(self.b, self.a, -gd)
        s.add_rhs(self.a, -Ieq)
        s.add_rhs(self.b, Ieq)
