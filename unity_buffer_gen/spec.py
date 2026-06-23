"""Specification and sizing data structures for the unity-gain buffer generator.

The "unity-gain buffer" here is a capacitor-stabilized analog voltage buffer
(an LDO-style voltage follower): a 5-transistor OTA in unity-gain feedback
drives a PMOS pass device so the output tracks a reference while sourcing load
current.  Naming follows the user request:

    * VIN  / vdd      supply rail (the "input", 1.2 V)
    * VREF / vref     reference the buffer follows (0.8 V by default)
    * VOUT / vout     regulated output (= VREF, 0.8 V), sources 0..10 mA
    * cout            output capacitor (1 uF)
    * error_res       target closed-loop output resistance (load regulation),
                      i.e. dVout/dIload must stay <= error_res (1 ohm).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class BufferSpec:
    """Top-level design targets for the buffer."""

    vdd: float = 1.2            # supply / input voltage [V]
    vout: float = 0.8           # regulated output voltage [V]
    vref: Optional[float] = None  # reference voltage; defaults to vout (unity gain)
    iload_max: float = 10e-3    # maximum load current [A]
    iload_min: float = 0.0      # minimum load current [A] (no-load)
    cout: float = 1e-6          # output capacitor [F]
    cout_esr: float = 0.0       # output-cap equivalent series resistance [ohm]
    error_res: float = 1.0      # target output resistance / load reg [ohm]

    # Verification acceptance targets (derived defaults are sensible).
    pm_min: float = 45.0        # minimum acceptable phase margin [deg]
    reg_tol: float = 25e-3      # max |Vout - Vref| (absolute accuracy incl.
                                # systematic OTA offset) [V]
    temp: float = 27.0          # nominal temperature [C]
    corner: str = "tt"          # process corner library section

    def __post_init__(self) -> None:
        if self.vref is None:
            self.vref = self.vout

    @property
    def dropout(self) -> float:
        """Headroom across the pass device at the regulated point [V]."""
        return self.vdd - self.vout

    @property
    def max_droop(self) -> float:
        """Allowed output droop over the full load range [V]."""
        return self.error_res * (self.iload_max - self.iload_min)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass
class DeviceSizes:
    """Per-device geometry. Widths/lengths in micrometres; nf fingers; m multiplier.

    Defaults are the verified operating point for the 1.2V->0.8V / 10mA design.
    Note the high |Vth| of the sky130 pfet on a 1.2 V rail forces a wide PMOS
    mirror (so its node stays mid-rail) and wide NMOS input devices (so the tail
    node has headroom for the tail current source).
    """

    # bias mirror (NMOS): diode reference + tail current source + output preload
    lb: float = 0.5
    wb: float = 10.0
    nfb: int = 1
    mb_ref: int = 2      # diode reference device multiplier (carries Iref)
    mb_tail: int = 4     # tail device multiplier (Itail = mb_tail/mb_ref * Iref)
    mb_pre: int = 20     # output preload sink (guarantees a DC sink at no load)

    # input differential pair (NMOS) -- wide for low Vgs / tail headroom
    li: float = 0.5
    wi: float = 10.0
    nfi: int = 1
    mi: int = 4

    # active load current mirror (PMOS) -- wide so the mirror node stays mid-rail
    lm: float = 1.0
    wm: float = 7.0
    nfm: int = 1
    mm: int = 32

    # pass device (PMOS)
    lp: float = 0.25
    wp: float = 5.0
    nfp: int = 4
    mp: int = 80

    # compensation cap, gate(OTA out)->VOUT [F]
    cc: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass
class BiasPlan:
    """Operating-point plan derived from the spec."""

    iref: float = 10e-6     # external reference current into IBIAS [A]
    itail: float = 20e-6    # OTA tail current [A]  (= mb_tail/mb_ref * iref)
    ipreload: float = 100e-6  # internal output preload sink [A]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass
class DesignResult:
    """Bundle returned by the generator: sizing + measured performance."""

    spec: BufferSpec
    sizes: DeviceSizes
    bias: BiasPlan
    metrics: dict = field(default_factory=dict)
    passed: bool = False
    iterations: int = 0
    history: list = field(default_factory=list)
