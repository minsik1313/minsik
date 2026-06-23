"""Extended verification of a generated design: corners, line regulation,
minimum VDD, quiescent current, loop gain and transient, plus plots.

Run after generating the design:
    python -m unity_buffer_gen --outdir output
    python examples/verify_design.py

Writes output/VERIFICATION.md, output/verification.json and (if matplotlib is
available) output/verification_plots.png.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unity_buffer_gen.spec import BufferSpec, DeviceSizes, BiasPlan
from unity_buffer_gen.pdk import find_pdk
from unity_buffer_gen import verify

OUT = os.path.join(os.path.dirname(__file__), "..", "output")
WD = os.path.join(OUT, "_verify")
os.makedirs(WD, exist_ok=True)

pdk = find_pdk(fast_lib_dir=WD)
spec = BufferSpec()
sz = DeviceSizes(); b = BiasPlan()
sz.__dict__.update(json.load(open(os.path.join(OUT, "sizes.json"))))
b.__dict__.update(json.load(open(os.path.join(OUT, "bias.json"))))

cor = verify.corners(pdk, spec, sz, b, WD)
lr = verify.line_reg(pdk, spec, sz, b, WD)
vdd_scan = {}
for vdd in (1.10, 1.15, 1.20, 1.25, 1.30):
    v, _ = verify._run_op(pdk, spec, sz, b, 1e-3,
                          os.path.join(WD, f"v{int(vdd*100)}"), vdd=vdd)
    vdd_scan[vdd] = v
f, g, p = verify.capture_ac(pdk, spec, sz, b, WD, spec.iload_max)
t, v = verify.capture_tran(pdk, spec, sz, b, WD)

dcg = g[0]; ugf = None
for i in range(1, len(g)):
    if g[i-1] >= 0 >= g[i]:
        ugf = f[i-1] + (f[i]-f[i-1])*(0-g[i-1])/(g[i]-g[i-1]); break
vref = spec.vref
up = [vv for tt, vv in zip(t, v) if 50e-6 < tt < 150e-6]
dn = [vv for tt, vv in zip(t, v) if 150e-6 < tt <= 200e-6]
undersh = (vref - min(up))*1e3 if up else float('nan')
oversh = (max(dn) - vref)*1e3 if dn else float('nan')

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].semilogx(f, g, 'b'); ax[0].axhline(0, color='k', lw=0.6)
    if ugf:
        ax[0].axvline(ugf, color='r', ls='--', lw=0.8, label=f"UGF {ugf/1e3:.0f}kHz")
    ax[0].set_title(f"Loop gain (DC {dcg:.0f} dB)"); ax[0].set_xlabel("Frequency [Hz]")
    ax[0].set_ylabel("|T| [dB]"); ax[0].grid(True, which='both', alpha=0.3); ax[0].legend()
    ax[1].plot([x*1e6 for x in t], [x*1e3 for x in v], 'b')
    ax[1].axhline(vref*1e3, color='k', ls=':', lw=0.8, label=f"VREF {vref*1e3:.0f}mV")
    ax[1].set_title(f"Transient load step 0<->10mA (under {undersh:.1f}/over {oversh:.1f} mV)")
    ax[1].set_xlabel("Time [us]"); ax[1].set_ylabel("Vout [mV]")
    ax[1].grid(True, alpha=0.3); ax[1].legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "verification_plots.png"), dpi=120)
    print("wrote verification_plots.png")
except Exception as e:
    print("plot skipped:", e)

json.dump({"corners": cor, "line_reg": lr, "vdd_scan": vdd_scan,
           "ac": {"dc_gain_db": dcg, "ugf_hz": ugf},
           "tran": {"undershoot_mv": undersh, "overshoot_mv": oversh}},
          open(os.path.join(OUT, "verification.json"), "w"), indent=2, default=str)
print("corners:", {c: (round(cor[c]['vout_fullload']*1e3, 1)
                       if 'error' not in cor[c] else 'PDK-blocked') for c in cor})
print("Edit output/VERIFICATION.md narrative as needed; data in verification.json")
