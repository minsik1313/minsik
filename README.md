# sky130 Unity-Gain Buffer — SPICE Testbench

Auto-generated ngspice testbench for the two-stage unity-gain voltage-follower
buffer (`unity_buffer`), targeting the SkyWater **sky130** PDK at VDD = 1.2 V.

## Files

| File | Purpose |
|------|---------|
| `unity_buffer.sp`    | DUT — the `.subckt unity_buffer` netlist (VDD VSS VIN VOUT IBIAS) |
| `tb_unity_buffer.sp` | Testbench — supplies, 10 µA bias reference, stimulus, 1 µF load, and 4 analyses |

## Prerequisites

- [ngspice](https://ngspice.sourceforge.io/) (any recent version)
- The **sky130 PDK** ngspice models. Set `PDK_ROOT` so this path resolves:
  ```
  $PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice
  ```
  If your ngspice build does not expand environment variables in `.lib`,
  edit that line in `tb_unity_buffer.sp` to an absolute path.

## Run

```sh
export PDK_ROOT=/path/to/your/pdk     # e.g. ~/.volare or /usr/share/pdk
ngspice tb_unity_buffer.sp
```

## What it tests

| # | Analysis | Checks | Output file |
|---|----------|--------|-------------|
| 1 | `.op`   | bias currents (tail = 4× ref, output sink = 100× ref), DC offset | console |
| 2 | `.dc`   | transfer VOUT vs VIN, gain ≈ 1, input range, follower error | `dc_transfer.txt` |
| 3 | `.tran` | ±100 mV step into 1 µF load — slew & settling time | `tran_step.txt` |
| 4a| `.ac`   | closed-loop gain flatness and −3 dB bandwidth | `ac_gain.txt` |
| 4b| `.ac`   | closed-loop output impedance Zout (design target ≈ 1 Ω) | `ac_zout.txt` |

`meas` statements print the key numbers (offset, gain, −3 dB freq, settling
time, low-frequency Zout) to the console; `wrdata` dumps the curves to text
files for plotting. Interactive `plot` lines are included but commented out.

## Notes / things you may want to tune

- **Bias polarity**: `IREF VDD IBIAS 10u` injects 10 µA *into* the IBIAS node
  (the diode-connected NMOS mirror to VSS). Flip it if your reference sources
  current the other way.
- **Operating point**: `VCM = 0.6 V`. The NMOS input pair favours a higher
  common-mode range; sweep #2 reveals the usable input window.
- **Step timing**: the 1 µF load with ~1 Ω closed-loop Zout gives a ~1 µs
  small-signal τ, but large steps are slew-limited — widen `.tran` stop time
  if `tsettle` does not trigger.
- **Stability**: this TB measures closed-loop behaviour. For phase margin you
  need a broken-loop (STB-style) analysis — ask and it can be added.
