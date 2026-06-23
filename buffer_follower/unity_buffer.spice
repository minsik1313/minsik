* Unity-gain voltage-follower buffer  (sky130, VDD=1.2 V)
* Two-stage: NMOS-input 5T OTA  ->  class-A common-source output
* Unity feedback (M1 gate = VOUT). Drives 1 uF; closed-loop Zout ~ 1 ohm.
* Pins: VDD VSS VIN VOUT IBIAS    (IBIAS = external ~10 uA reference current)
* W/L in micrometres (.option scale=1.0u required by the sky130 models).
.subckt unity_buffer VDD VSS VIN VOUT IBIAS
* ---- bias mirror (NMOS) : reference + OTA tail + output sink ----
XMB0  IBIAS IBIAS VSS VSS sky130_fd_pr__nfet_01v8 L=0.5 W=10 nf=1 m=2
XMB1  TAIL  IBIAS VSS VSS sky130_fd_pr__nfet_01v8 L=0.5 W=10 nf=1 m=4
XMON  VOUT  IBIAS VSS VSS sky130_fd_pr__nfet_01v8 L=0.5 W=10 nf=1 m=100
* ---- stage 1: NMOS input pair (M1 gate=VOUT feedback, M2 gate=VIN) ----
XM1   NA    VOUT  TAIL VSS sky130_fd_pr__nfet_01v8 L=1.0 W=20 nf=2 m=4
XM2   OTA   VIN   TAIL VSS sky130_fd_pr__nfet_01v8 L=1.0 W=20 nf=2 m=4
* ---- stage 1 load: PMOS current mirror (wide: high |Vth| pfet) ----
XM3   NA    NA    VDD  VDD sky130_fd_pr__pfet_01v8 L=2.0 W=7  nf=1 m=32
XM4   OTA   NA    VDD  VDD sky130_fd_pr__pfet_01v8 L=2.0 W=7  nf=1 m=32
* ---- stage 2: PMOS common-source pull-up (gate = OTA out) ----
XMP   VOUT  OTA   VDD  VDD sky130_fd_pr__pfet_01v8 L=0.5 W=10 nf=2 m=300
.ends unity_buffer
