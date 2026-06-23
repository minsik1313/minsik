"""topology.py — Structure (topology) library + SPICE deck generation.

Two single-ended gain structures, escalating in gain at the cost of area /
complexity. The autosizer tries them in order and stops at the first that
meets spec, which *is* the structure-selection decision:

  common_source : 1 stage,  gain ≈ gm·Rd
  two_stage     : 2 stages,  gain ≈ (gm·Rd)²   (AC-coupled, re-biased)

Each generator emits a self-contained ngspice deck for the chosen voltage
domain's device model. The `.measure` lines expose:
  - vout_dc  : stage-output DC operating point (headroom check)
  - gain_db  : small-signal voltage gain
"""
from tech import VoltageDomain

_CTRL = """.control
  op
  let vout_dc = v(out)
  print vout_dc
  ac dec 20 1 1G
  meas ac gain_db max vdb(out)
  print gain_db
.endc
.end
"""


def common_source(dom: VoltageDomain, w_um: float, vbias: float) -> str:
    rd = dom.rload_k
    return f"""* common_source  domain={dom.name}  device={dom.nfet}
Vdd vdd 0 {dom.vdd_nom}
Vin in 0 dc {vbias:.4f} ac 1
M1 out in 0 0 nch W={w_um}u L=1u
Rd vdd out {rd}k
{dom.demo_model}
{_CTRL}"""


def two_stage(dom: VoltageDomain, w_um: float, vbias: float) -> str:
    rd = dom.rload_k
    return f"""* two_stage  domain={dom.name}  device={dom.nfet}
Vdd vdd 0 {dom.vdd_nom}
Vin in 0 dc {vbias:.4f} ac 1
* stage 1
M1 o1 in 0 0 nch W={w_um}u L=1u
Rd1 vdd o1 {rd}k
* AC coupling + independent re-bias of stage 2
Cc o1 g2 1
Vb2 b2 0 dc {vbias:.4f}
Rb b2 g2 1G
* stage 2
M2 out g2 0 0 nch W={w_um}u L=1u
Rd2 vdd out {rd}k
{dom.demo_model}
{_CTRL}"""


# Tried in increasing-gain order.
TOPOLOGIES = [
    ("common_source", common_source),
    ("two_stage", two_stage),
]
