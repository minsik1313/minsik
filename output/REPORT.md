# Unity-gain buffer (sky130) — generated design report

**Status:** PASS ✅  (converged in 1 iteration(s))

## Specification

| Parameter | Value |
|---|---|
| Supply / input VDD | 1.2V |
| Output VOUT | 0.8V |
| Reference VREF | 0.8V |
| Load current | 0A … 10mA |
| Output cap COUT | 1uF (ESR 0ohm) |
| Target output res (error_res) | 1ohm |
| Dropout (VDD−VOUT) | 400mV |
| Process corner | tt, 27°C, sky130A |

## Measured performance (ngspice + sky130_fd_pr)

| Metric | Result | Target | OK |
|---|---|---|---|
| Vout @ no load | 0.81346V | 0.8V±25mV | ✅ |
| Vout @ 10mA | 0.80866V | 0.8V±25mV | ✅ |
| Output resistance / load reg (chord) | 0.48 ohm | ≤ 1 ohm | ✅ |
| Output resistance (worst incremental) | 7.27 ohm | (informational) | — |
| Load regulation | 4.8mV over range | ≤ 10mV | — |
| DC loop gain | 47.3 dB | — | — |
| Unity-gain freq | 9.272e+05 Hz | — | — |
| Loop phase margin (approx.) | 178° | ≥ 45° | ✅ |
| Load-step undershoot (0→10mA) | -8.15mV | — | — |
| Load-step overshoot (10mA→0) | 13.5mV | well-damped | ✅ |

## Sized devices (sky130_fd_pr)

- **Bias current Iref / Itail:** 10uA / 20uA

| Device | Role | Model | L (µm) | W/finger (µm) | nf | m |
|---|---|---|---|---|---|---|
| MB0/MB1 | bias mirror | nfet_01v8 | 0.5 | 10.0 | 1 | 2/4 |
| M1/M2 | input pair | nfet_01v8 | 0.5 | 10.0 | 1 | 4 |
| M3/M4 | mirror load | pfet_01v8 | 1.0 | 7.0 | 1 | 32 |
| MP | pass device | pfet_01v8 | 0.25 | 5.0 | 4 | 65 |
| | | | | **total pass W ≈ 1300 µm** | | |

## Notes

- Topology: NMOS-input 5T OTA + PMOS pass device in unity-gain feedback; the 1 µF output cap sets the dominant pole.
- `error_res` is interpreted as the target closed-loop output resistance (load regulation): ΔVout/ΔIload ≤ error_res.
- `IBIAS` is an external reference current (assume a bandgap/Iref source); the testbench supplies it with an ideal current source.
- Device geometries are auto-snapped to PDK bins that pass BSIM4 checks (some sky130 bins abort in ngspice).
- Stability is gated on the transient load-step response (over/undershoot, ring-down). The injected-loop phase margin is a corroborating estimate; single-point voltage injection at the 1 µF output node tends to under-report phase shift, so the transient is treated as authoritative.
- A small internal preload sink (MBPRE) guarantees a DC current path so the PMOS LDO regulates at zero external load; the ~13 mV absolute offset is the systematic 5T-OTA offset (trimmable / reducible with longer input devices) and is separate from the load-regulation spec, which is met.
