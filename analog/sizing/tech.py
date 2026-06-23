"""tech.py — Voltage-domain-aware device library (sky130-mapped).

The core of the analog automation: a target supply voltage selects a voltage
DOMAIN, and each domain pins down which sky130 device *flavor* is legal
(thin-oxide 1.8 V core vs. thick-oxide 5 V I/O), its Vds rating, and the
bias headroom assumptions used by the sizing engine.

For the runnable demo we attach a generic Level-1 SPICE model per domain whose
parameters qualitatively track the real devices (thin oxide -> higher kp/lower
Vth; thick oxide -> lower kp/higher Vth). For production, swap `demo_model`
for the sky130 .lib include and instantiate `nfet`/`pfet` by name.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VoltageDomain:
    name: str
    vdd_nom: float       # nominal supply for this domain (V)
    vds_max: float       # device drain-source rating (V) — hard safety limit
    nfet: str            # sky130 NMOS flavor for this domain
    pfet: str            # sky130 PFET flavor
    vth_n: float         # nominal NMOS threshold (V), for biasing
    vov: float           # target overdrive (V) — larger for thick-oxide
    rload_k: float       # default resistive load (kΩ) for the demo decks
    demo_model: str      # Level-1 model cards used by the runnable demo


# Ordered from thinnest/lowest-voltage to thickest/highest-voltage.
DOMAINS = [
    VoltageDomain(
        name="core_1v8",
        vdd_nom=1.8, vds_max=1.95,
        nfet="sky130_fd_pr__nfet_01v8",
        pfet="sky130_fd_pr__pfet_01v8",
        vth_n=0.45, vov=0.20, rload_k=10.0,
        demo_model=(
            ".model nch nmos (level=1 kp=120u vto=0.45 lambda=0.08)\n"
            ".model pch pmos (level=1 kp=40u vto=-0.45 lambda=0.10)"
        ),
    ),
    VoltageDomain(
        name="io_5v0",
        vdd_nom=5.0, vds_max=5.5,
        nfet="sky130_fd_pr__nfet_g5v0d10v5",
        pfet="sky130_fd_pr__pfet_g5v0d10v5",
        vth_n=0.70, vov=0.35, rload_k=20.0,
        demo_model=(
            ".model nch nmos (level=1 kp=50u vto=0.70 lambda=0.04)\n"
            ".model pch pmos (level=1 kp=18u vto=-0.70 lambda=0.05)"
        ),
    ),
]

# Safety margin: require the device rating to clear the supply by this factor.
VDS_MARGIN = 1.05


def select_domain(vdd: float) -> VoltageDomain:
    """Pick the thinnest-oxide domain whose Vds rating safely covers `vdd`.

    This is the device-selection step: a 3.3 V rail, having no dedicated
    sky130 flavor, is mapped onto the 5 V thick-oxide device because the
    1.8 V core device would be over-stressed.
    """
    for dom in DOMAINS:  # thin -> thick
        if dom.vds_max >= vdd * VDS_MARGIN:
            return dom
    raise ValueError(
        f"No sky130 device flavor rated for Vdd={vdd} V "
        f"(max available {DOMAINS[-1].vds_max} V)."
    )
