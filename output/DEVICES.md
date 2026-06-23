# Device settings & operating point (at Iload = 10 mA, tt)

## Transistors

| Device | Role | Model | W/L (µm) | nf×m | Id | Vgs (V) | Vds (V) | gm | ro=1/gds | Cgg (fF) | Cgd (fF) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MB0 | bias diode | nfet_01v8 | 10/0.5 | 1×2 | 10.0 µA | 0.606 | 0.606 | 214 µS | 474.7 kΩ | 46 | 0.0 |
| MB1 | tail current src | nfet_01v8 | 10/0.5 | 1×4 | 17.7 µA | 0.606 | 0.187 | 382 µS | 114.7 kΩ | 93 | 2.2 |
| MBPRE | output preload | nfet_01v8 | 10/0.5 | 1×20 | 104.1 µA | 0.606 | 0.809 | 2.2 mS | 51.3 kΩ | 457 | 0.4 |
| M1 | input (g=VOUT) | nfet_01v8 | 10/0.5 | 1×4 | 8.9 µA | 0.622 | 0.064 | 198 µS | 26.6 kΩ | 98 | 25.3 |
| M2 | input (g=VREF) | nfet_01v8 | 10/0.5 | 1×4 | 8.8 µA | 0.613 | 0.280 | 203 µS | 326.5 kΩ | 86 | 0.3 |
| M3 | mirror diode | pfet_01v8 | 7/1 | 1×32 | 8.9 µA | 0.949 | 0.949 | 155 µS | 3.03 MΩ | 819 | 0.0 |
| M4 | mirror out | pfet_01v8 | 7/1 | 1×32 | 8.8 µA | 0.949 | 0.733 | 154 µS | 2.63 MΩ | 819 | 0.1 |
| MP | pass device | pfet_01v8 | 5/0.25 | 4×65 | 10.15 mA | 0.733 | 0.391 | 143.1 mS | 31.5 Ω | 308 | 0.3 |

## Passives / sources

| Component | Value | Notes |
|---|---|---|
| COUT | 1 µF (ESR 0 Ω) | output cap, sets dominant pole |
| IREF | 10 µA | external reference current into IBIAS |
| Itail | 20 µA | OTA tail (mirrored from IREF) |
| Ipreload | ~100 µA | internal MBPRE sink at VOUT |
| error_res (target) | 1 Ω | spec: ΔVout/ΔIload |
| (discrete resistors) | none | output resistance is the closed-loop ro; no passive R in the cell |


_Cgs/Cgd use ngspice's signed trans-capacitance convention; magnitudes shown. ro = 1/gds._
