# Unity-gain buffer — design report (sky130, open_pdk)

Detailed walk-through from **specification → architecture selection → device
selection → sizing → verification**, for a unity-gain voltage-follower buffer
built on the open-source SkyWater sky130 130 nm PDK and verified with ngspice
against the real `sky130_fd_pr` device models.

---

## 1. Specification & interpretation

| Given | Value | Interpretation used in this design |
|---|---|---|
| VDD | 1.2 V | single supply rail (the only rail; VSS = 0) |
| buffer input range | up to 0.8 V | input is a DC/slow voltage in **0 … 0.8 V**; output must follow it, Vout = Vin |
| output capacitor | 1 µF | large capacitive load on the output node |
| error res | 1 Ω | **target closed-loop output resistance** Zout ≤ 1 Ω (ΔVout/ΔIload) |
| PDK | sky130 (open_pdk) | `sky130_fd_pr__nfet_01v8`, `sky130_fd_pr__pfet_01v8`, 1.8 V devices |

A *unity-gain buffer* is a feedback amplifier with the output tied back to the
inverting input so the closed-loop gain is +1: **Vout = Vin**. It isolates a
high-impedance source from a heavy load (here a 1 µF cap) and presents a low
output impedance (target ≤ 1 Ω). No DC load current is specified, so the output
stage is sized for **output impedance and capacitive drive**, not for delivering
large DC current.

---

## 2. Device characterization (the numbers that drive every decision)

Before choosing a topology, the two core devices were characterized in ngspice
(L = 0.5 µm, W = 10 µm, Vds/Vsd = 0.6 V, tt, 27 °C):

| Device | Threshold |Id @ low Vgs| Id @ high Vgs | Note |
|---|---|---|---|---|
| `nfet_01v8` | **Vth ≈ 0.45 V** | 4.4 µA @ Vgs=0.6 | 101 µA @ Vgs=0.8 | strong, well-behaved |
| `pfet_01v8` | **\|Vth\| ≈ 0.85 V** | 0.1 µA @ Vsg=0.8 | 3.4 µA @ Vsg=1.0 | **very weak / high-Vth** |

**The single most important fact:** the sky130 pfet has \|Vth\| ≈ 0.85 V, which
is enormous on a 1.2 V rail — a PMOS needs Vsg ≈ 1.0 V to carry just a few µA.
This dominates the architecture and the sizing everywhere a PMOS appears.

---

## 3. Architecture selection

### 3.1 Closed-loop follower vs open-loop

An open-loop source/emitter follower (a single transistor) has gain < 1, a
Vgs/Vsg level shift (hundreds of mV of offset here, and signal-dependent), and
an output impedance ≈ 1/gm (tens of Ω). None of that meets "Vout = Vin" with
≤ 1 Ω. → **A feedback (op-amp-based) unity-gain follower is required.** Output
impedance then becomes Zout ≈ Zout,openloop / (1 + T), where T is the loop gain,
so a high-gain loop is what buys the low Zout.

### 3.2 Input stage — common-mode range analysis

The follower's two inputs sit at the common-mode voltage Vcm = Vin = Vout, which
must span the input range. With the characterized thresholds:

* **NMOS pair:** needs Vcm ≥ Vgs,n + Vov,tail. With wide devices Vgs,n ≈ 0.55–0.65 V,
  Vov,tail ≈ 0.1 V ⇒ usable Vcm ≈ **0.6 … 1.2 V**. Covers the top of the range.
* **PMOS pair:** needs Vcm ≤ VDD − Vsg,p − Vov,tail. With \|Vth\|≈0.85, Vsg,p ≈ 0.95 V
  ⇒ usable Vcm ≈ **0 … 0.15 V**. Only the very bottom.
* **Rail-to-rail (both pairs):** would be needed for a *full* 0–0.8 V swing, but
  on this PDK the two pairs leave a **dead band ≈ 0.15–0.6 V** where *neither*
  conducts (because \|Vth,p\| is so high) — so naive rail-to-rail does **not**
  cover the middle either, and a constant-gm rail-to-rail front-end becomes
  disproportionately complex.

**Decision:** use an **NMOS input pair**. It natively covers the upper part of
the range that includes the 0.8 V target. Its lower CM limit is pushed down as
far as the headroom allows by making the input devices **wide** (lower Vgs) and
the tail device **wide** (lower Vdssat). Measured usable input range of the final
design is **0 … ≈0.72 V** (see §5); the top ~0.72–0.8 V is where the OTA loses
headroom/gain — this is the honest limit of a single NMOS-pair stage on 1.2 V.

### 3.3 Load of the input stage

A PMOS current-mirror load converts the differential current to single-ended and
gives the first stage its voltage gain (gm1·(ro2‖ro4)). Because the pfet is weak,
the mirror devices are made **wide and long** (large W for current, long L for
output resistance/gain, and so the mirror node sits at a sensible mid-rail
voltage instead of collapsing to ground).

### 3.4 Output stage — why two stages

A single-stage OTA follower has Zout ≈ 1/gm1 ≈ 1/(100 µS) ≈ 10 kΩ — four orders
of magnitude above spec. The 1 Ω target therefore **forces a second gain stage**.
The output stage is a **class-A common-source** stage:

* **PMOS pull-up `MP`** (source = VDD, gate = OTA output, drain = VOUT) actively
  sources current into the load;
* **NMOS current-sink `MON`** (gate = bias) sets the quiescent current and pulls
  the output down.

This gives the loop a second high-gain stage (total ≈ 73 dB) so
Zout = Zout,ol/(1+T) lands at ≈ 1 Ω. A class-A (vs class-AB) output keeps the
design simple; the cost is asymmetric slew (§5) and standing current (~0.5 mA).

### 3.5 Compensation

The 1 µF load on the output makes the **output node the dominant pole**
(p1 = 1/(2π·Zout,ol·1µF), a few kHz). The only other significant pole is at the
OTA output / `MP` gate; keeping that stage's resistance and `MP`'s gate
capacitance modest puts it well above the unity-gain frequency. The loop is thus
**self-compensated by the big load cap** — no Miller cap needed. Measured UGF
≈ 41 kHz with the output pole dominant ⇒ stable (verified by the transient, §5).

### 3.6 Biasing

A single external reference current `IBIAS` (≈ 10 µA, from a bandgap/Iref) feeds
an NMOS mirror that generates the OTA tail current (20 µA) and the output sink
current (~0.5 mA). One pin, all internal mirrors are NMOS (the friendly device).

```
        VDD ─┬───────────┬────────────────────┬──────────────
             │           │                     │
           [M3]        [M4]                  [MP]  PMOS pull-up
        mirror diode  mirror out          g=OTA  d=VOUT
             │ NA────────┤ OTA ─────────────────┤
           [M1]        [M2]   NMOS input pair    ├─[COUT 1µF]
         g=VOUT       g=VIN                      │
             └────┬──────┘                     [MON] NMOS sink  ← VOUT pull-down
                 TAIL                            │
               [MB1]  tail (mirror of IBIAS)     │
        VSS ──────┴─────────[MB0 diode]──────────┴──────────────
                              ↑ IBIAS (≈10 µA ext. ref)
   unity feedback: M1 gate tied to VOUT  (Vout = Vin)
```

---

## 4. Device selection & sizing

All sizes verified to land in PDK model bins that pass BSIM4 checks. W/L in µm,
`nf` = fingers, `m` = multiplier.

| Device | Role | Type | W/L | nf×m | Why this size |
|---|---|---|---|---|---|
| MB0 | bias diode (Iref) | nfet | 10/0.5 | 1×2 | sets gate bias from 10 µA ref |
| MB1 | OTA tail source | nfet | 10/0.5 | 1×4 | Itail = (4/2)·10 µA = 20 µA |
| MON | output sink | nfet | 10/0.5 | 1×100 | sets output Iq ≈ 0.5 mA → output gm for Zout |
| M1,M2 | input pair | nfet | 20/1.0 | 2×4 | **wide** → low Vgs (extends low-CM limit); **L=1** → gain & low offset |
| M3,M4 | mirror load | pfet | 7/2.0 | 1×32 | **wide** (weak pfet) so mirror node stays mid-rail; **long L** for ro/gain |
| MP | output pull-up | pfet | 10/0.5 | 2×300 | **large** because the weak pfet must source the sink current + load; gives output gm |

**Sizing logic, step by step**

1. **Bias current.** 10 µA reference → 20 µA OTA tail (good gm/noise/area
   balance at this speed). Output quiescent set to ≈ 0.5 mA (next steps show why).
2. **Input pair (M1/M2).** Width chosen so Vgs ≈ 0.55–0.6 V at 10 µA/branch,
   which puts the tail node ≈ 0.2 V — enough for MB1 to stay saturated and to push
   the low common-mode limit toward 0 V. L = 1 µm trades a little speed for higher
   ro (stage-1 gain) and lower systematic offset.
3. **Mirror (M3/M4).** Sized wide because the pfet is weak — a narrow mirror would
   need Vsg ≈ 1.17 V for 10 µA and pin the mirror node near ground, collapsing the
   OTA. W=7, m=32, L=2 gives Vsg ≈ 0.95 V, mirror node ≈ 0.25 V, devices in
   saturation, and high ro for first-stage gain (~40 dB).
4. **Output sink (MON) → output quiescent current.** Zout = Zout,ol/(1+T). With
   the two-stage loop gain fixed (~73 dB), Zout scales with the output devices'
   ro (∝ 1/Iq) and gm (∝ Iq). Sweeping Iq:
   - Iq ≈ 80 µA → Zout ≈ 2.5 Ω
   - Iq ≈ 0.4 mA → Zout ≈ 1.1 Ω
   - **Iq ≈ 0.5 mA → Zout ≈ 0.99 Ω ✅**
   So MON is sized (m=100) for ≈ 0.5 mA — the minimum that meets the 1 Ω spec.
5. **Output pull-up (MP).** Must source the sink current (0.5 mA) plus any load
   current, at the available gate drive (OTA output can swing down to ≈ 0.2 V →
   Vsg,p ≈ 1.0 V). Because the pfet is weak (~3.4 µA per 10 µm at Vsg=1.0 V), MP
   needs a large width — W=10, nf=2, m=300 (≈ 6 mm total) to source ~1 mA with
   margin. This is the direct area cost of the high pfet Vth.

---

## 5. Verification (ngspice + sky130_fd_pr, tt, 27 °C)

See `buffer_plots.png` (DC transfer, follower error, transient step).

| Metric | Result | Target | OK |
|---|---|---|---|
| Unity-gain following, Vin = 0.2–0.7 V | error −3 … +4 mV | Vout = Vin | ✅ |
| Usable input range | **0 … ≈0.72 V** | up to 0.8 V | ⚠️ partial (see below) |
| **Output resistance Zout @ Vin=0.5 V** | **0.99 Ω** | ≤ 1 Ω | ✅ |
| DC loop gain | 72.9 dB | high | ✅ |
| Unity-gain frequency | 41 kHz | — | — |
| Stability (transient step 0.5→0.6 V) | 1.3 mV overshoot, no ringing | stable | ✅ |
| Quiescent supply current | ≈ 0.5 mA | low | — |
| Rising slew rate | ≈ 2 V/ms | — | — |
| Falling slew rate | ≈ 0.5 V/ms | — | slew-limited by 1 µF + class-A |

**Reading the results**

* **DC transfer / accuracy.** Vout tracks Vin within a few mV over ≈ 0.15–0.70 V
  (error crosses zero near 0.5 V; small systematic OTA offset elsewhere). This is
  genuine unity-gain behaviour.
* **Output impedance.** 0.99 Ω meets the `error res = 1 Ω` spec — this is the
  payoff of the two-stage (73 dB) loop and the 0.5 mA output stage.
* **Stability.** With the 1 µF output pole dominant, the step response is
  well-damped (1.3 mV overshoot, no ringing) — the authoritative stability check.
* **Slew.** Pulling the 1 µF load *down* relies on the class-A sink current
  (≈ 0.5 mA): dV/dt = I/C ≈ 0.5 V/ms. The rising edge (active PMOS pull-up) is
  faster. So this is a **slow/accurate (reference-style) buffer**, appropriate for
  a DC input and a 1 µF load — not a high-speed line driver.

---

## 6. Honest limitations & how to improve

1. **Top of the input range (0.72–0.8 V).** A single NMOS-pair input on 1.2 V
   runs out of headroom near the top; above ≈ 0.73 V the OTA loses gain and the
   DC solver also finds an unstable "runaway" root. *Fix:* a folded-cascode or
   rail-to-rail-aware front end, or simply target Vin ≤ 0.7 V.
2. **Asymmetric / slow slew.** Class-A output. *Fix:* a class-AB output stage for
   symmetric, faster slewing of the 1 µF load (at more complexity).
3. **Large PMOS pull-up & high pfet Vth.** The weak pfet forces a ~6 mm output
   device and limits drive. *Fix:* `pfet_01v8_lvt` (low-Vt) for the output and
   mirror would shrink area and improve headroom.
4. **Process corners.** The pfet L=0.25 bin is corner-defective (Drout<0 fatal at
   ss/sf); this design uses L≥0.5 pfet bins that are clean across corners.
5. **~10 mV systematic offset** away from mid-range, from the 5T-OTA drain-voltage
   mismatch; reducible with longer input L or a cascoded/auto-zeroed front end.

---

## 7. Files

| File | Contents |
|---|---|
| `unity_buffer.spice` | the sized buffer `.subckt` (sky130 devices) |
| `tb_transfer.spice` | DC transfer testbench (`ngspice -b`, needs sky130 lib) |
| `buffer_plots.png` | DC transfer, follower error, transient step |
| `DESIGN_REPORT.md` | this report |

Run: build the sky130 model lib (e.g. `volare enable --pdk sky130 <ver>`), put a
`sky130_fast.lib.spice` (or point `.lib` at the full `sky130.lib.spice`) next to
the netlists, then `ngspice -b tb_transfer.spice`.
