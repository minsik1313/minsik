"""Generate the requested 1.2V->0.8V / 10mA / 1uF / 1ohm buffer.

Run:  python examples/generate_default.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unity_buffer_gen import BufferSpec, design_buffer
from unity_buffer_gen.pdk import find_pdk
from unity_buffer_gen import report

spec = BufferSpec(
    vdd=1.2,
    vout=0.8,
    iload_max=10e-3,
    cout=1e-6,
    error_res=1.0,
)

outdir = os.path.join(os.path.dirname(__file__), "..", "output")
res = design_buffer(spec, workdir=os.path.join(outdir, "_work"))
pdk = find_pdk()
report.emit_artifacts(res, pdk, outdir)
print("\n" + report.render_report(res, pdk))
print("Artifacts in:", os.path.abspath(outdir))
