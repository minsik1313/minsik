# Unity-gain buffer generator (SkyWater sky130)

Automatically **designs, sizes and verifies** a unity-gain analog voltage
buffer (a capacitor-stabilized LDO-style voltage follower) on the open-source
**SkyWater sky130** PDK, using `ngspice` and the real `sky130_fd_pr` device
models.

Given a target spec, the tool:

1. characterizes the real PMOS pass device to size it for the load current,
2. assembles a 5-transistor OTA + PMOS pass + bias-mirror netlist,
3. **verifies** DC regulation, output resistance (load regulation), loop phase
   margin and the transient load-step response in `ngspice`,
4. **auto-tunes** a handful of knobs until the spec is met, then emits the
   netlists and a Markdown report.

## Default specification (the requested design)

| Parameter | Value |
|---|---|
| Supply / input `VDD` | 1.2 V |
| Output / reference `VOUT` (= `VREF`) | 0.8 V |
| Load current | 0 … 10 mA |
| Output capacitor `COUT` | 1 µF |
| Target output resistance `error_res` | 1 Ω |
| Dropout | 400 mV |
| PDK | open_pdk sky130 (`sky130_fd_pr`, 130 nm) |

> **Interpretation of the spec.** This is a *unity-gain buffer*: the OTA runs in
> unity feedback so `VOUT` tracks the 0.8 V reference while the PMOS pass device
> sources up to 10 mA from the 1.2 V supply. `error_res = 1 Ω` is taken as the
> **target closed-loop output resistance** (load regulation), i.e.
> `ΔVout / ΔIload ≤ 1 Ω` (≤ 10 mV droop over the full 10 mA range). The 1 µF
> output capacitor sets the dominant pole and stabilizes the loop.

## Topology

```
        VDD ─┬───────────┬──────────────────┬─────────
             │           │                  │
           [M3]        [M4]               [MP]  PMOS pass
        diode mir.   mir. out         g=OTA  d=VOUT
             │           │                  │
             NA ─────────┴──► OTA ──(CC)──► VOUT ──┬──[COUT 1µF]──GND
             │           │                         └──► load 0..10mA
           [M1]        [M2]   NMOS input pair
         g=VOUT       g=VREF      (unity-gain feedback: M1.gate = VOUT)
             └────┬──────┘
                 TAIL
               [MB1] tail current  ◄── mirror of IBIAS (MB0 diode)
                  │
        VSS ──────┴───────────────────────────────────
```

* NMOS-input 5-transistor OTA (M1/M2 pair, M3/M4 PMOS mirror load).
* PMOS pass device `MP` for low dropout (gate driven by the OTA output).
* Unity-gain feedback: `M1`'s gate is tied directly to `VOUT`.
* Tail current set by an external reference current `IBIAS` (bandgap/Iref),
  mirrored by `MB0`/`MB1`.

## Requirements

* `ngspice` (tested with v42)
* sky130 models via [`volare`](https://github.com/efabless/volare):

  ```bash
  pip install volare
  volare enable --pdk sky130 <version>
  ```

  The generator auto-discovers `sky130.lib.spice` under `~/.volare`,
  `$PDK_ROOT`, or `$SKY130_LIB`.

## Usage

```bash
# default 1.2V->0.8V, 10mA, 1uF, 1ohm design
python -m unity_buffer_gen --outdir output

# custom spec
python -m unity_buffer_gen --vdd 1.2 --vout 0.8 --iload 10e-3 \
    --cout 1e-6 --error-res 1.0 --corner tt --outdir output
```

Or from Python:

```python
from unity_buffer_gen import BufferSpec, design_buffer
res = design_buffer(BufferSpec(vdd=1.2, vout=0.8, iload_max=10e-3,
                               cout=1e-6, error_res=1.0))
print(res.passed, res.metrics)
```

## Output artifacts (`output/`)

| File | Contents |
|---|---|
| `unity_buffer.spice` | the sized buffer `.subckt` (sky130 devices) |
| `tb_op_noload.spice` / `tb_op_fullload.spice` | DC operating-point testbenches |
| `tb_dc_load.spice` | load sweep → output resistance / load regulation |
| `tb_ac_loop.spice` | loop-gain AC (Middlebrook injection) → phase margin |
| `tb_tran_step.spice` | 0→10 mA load-step transient |
| `sizes.json`, `bias.json`, `spec.json`, `metrics.json` | machine-readable design |
| `REPORT.md` | the verification report |

Re-run any testbench manually with `ngspice -b output/tb_*.spice`.

## How the auto-tuner works

Each iteration measures the spec in `ngspice` and adjusts the most impactful
knob:

* **Vout droops at full load** → grow the pass-device multiplier `mp`.
* **Output resistance too high** → raise loop gain (lower tail current — the 5T
  OTA gain rises as `1/√I` — lengthen the mirror, grow `mp`).
* **Phase margin too low** → add/grow the Miller compensation cap `CC`.

Device geometries are snapped to PDK bins that pass BSIM4's parameter checks
(a few sky130 bins abort in `ngspice`), so emitted netlists always simulate.
