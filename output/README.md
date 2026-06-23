# Sample generated output

Produced by:

```bash
python -m unity_buffer_gen --outdir output
```

for the default 1.2 V → 0.8 V / 0–10 mA / 1 µF / 1 Ω spec.

| File | Contents |
|---|---|
| `REPORT.md` | verified performance summary |
| `DEVICES.md` | per-device settings + operating point (W/L/nf/m, Id, gm, ro, caps) |
| `schematic.svg` / `schematic.png` | annotated circuit schematic |
| `unity_buffer.spice` | the sized buffer `.subckt` |
| `tb_*.spice` | op / dc-load / ac-loop / transient testbenches |
| `*.json` | machine-readable spec / sizing / bias / metrics |

To **run** the testbenches you also need the trimmed model library
`sky130_fast.lib.spice`, which embeds absolute paths to your local sky130 PDK
and is therefore git-ignored. Regenerate it (and everything here) by re-running
the command above, then:

```bash
cd output
ngspice -b tb_op_fullload.spice     # or tb_dc_load / tb_ac_loop / tb_tran_step
```
