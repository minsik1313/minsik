* ============================================================
* 5-Transistor OTA (5T amplifier)
*   - NMOS input differential pair : M1, M2
*   - PMOS current-mirror load      : M3, M4
*   - NMOS tail current source      : M5
*
* MOSFET syntax:  M<name> <drain> <gate> <source> <bulk> <model> [params]
* ============================================================

* --- input differential pair (NMOS) ---
M1  OUTM  INP   TAIL  VSS  nmos  W=4u  L=0.5u
M2  OUTP  INN   TAIL  VSS  nmos  W=4u  L=0.5u

* --- current-mirror load (PMOS), M3 diode-connected ---
M3  OUTM  OUTM  VDD   VDD  pmos  W=8u  L=0.5u
M4  OUTP  OUTM  VDD   VDD  pmos  W=8u  L=0.5u

* --- tail current source (NMOS) ---
M5  TAIL  VBIAS VSS   VSS  nmos  W=8u  L=0.5u

* --- device models ---
.model nmos nmos
.model pmos pmos

* --- supplies / port hints (optional) ---
.global VDD VSS
.end
