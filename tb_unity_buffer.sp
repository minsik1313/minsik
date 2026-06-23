* =====================================================================
* Testbench : unity-gain voltage-follower buffer (sky130, VDD = 1.2 V)
* DUT       : unity_buffer  (VDD VSS VIN VOUT IBIAS)
* Simulator : ngspice
*
* Covers four analyses, each in its own .control sub-run:
*   1) .op   - operating point + bias-current sanity check
*   2) .dc   - DC transfer VOUT vs VIN  (gain ~1, input range, offset)
*   3) .tran - large-signal step response driving the 1 uF load
*   4) .ac   - closed-loop gain/bandwidth  +  output impedance Zout
*
* Run:   ngspice tb_unity_buffer.sp
* (needs the sky130 PDK; set PDK_ROOT or edit the .lib path below)
* =====================================================================

.title unity_buffer_testbench

* ---- global options / corner ----
.option scale=1.0u          ; W/L in the netlist are given in micrometres
.temp 27

* ---- sky130 device models (typical corner) ----
* ngspice expands the environment variable PDK_ROOT; if your build does not,
* replace the line below with the absolute path to sky130.lib.spice.
.lib "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* ---- device under test ----
.include "unity_buffer.sp"

* ---------------------------------------------------------------------
* Test fixture
* ---------------------------------------------------------------------
.param VDD_VAL = 1.2
.param VCM     = 0.6        ; nominal input/common-mode operating point
.param IB      = 10u        ; external reference current into IBIAS

VVDD  VDD 0 DC {VDD_VAL}
VVSS  VSS 0 DC 0

* Reference current: 10 uA injected INTO the IBIAS node, which is the
* diode-connected NMOS (XMB0) that sets up the bias mirror to VSS.
IREF  VDD IBIAS DC {IB}

* Stimulus.  AC=1 lets the same source drive the .ac sweep; the PULSE
* source (only seen by .tran) provides the large-signal step.
VIN   VIN 0 DC {VCM} AC 1 PULSE({VCM-0.1} {VCM+0.1} 100u 1n 1n 1 2)

* Load specified in the design brief.
CL    VOUT 0 1u

* Probe source for output-impedance measurement (off unless .ac uses it).
IPROBE VOUT 0 DC 0 AC 0

X1 VDD VSS VIN VOUT IBIAS unity_buffer

* =====================================================================
* 1) OPERATING POINT  -  check the bias currents fan out as designed
* =====================================================================
.control
  op
  echo "==== Operating point ===="
  print v(VOUT) v(X1.TAIL) v(X1.NA) v(X1.OTA)
  echo "-- buffer DC error at VCM (should be a few mV) --"
  let voffset = v(VOUT) - v(VIN)
  print voffset
  * tail current (4x ref) and output sink (100x ref) branch currents
  print @m.x1.xmb1.msky130_fd_pr__nfet_01v8[id]
  print @m.x1.xmon.msky130_fd_pr__nfet_01v8[id]
.endc

* =====================================================================
* 2) DC TRANSFER  -  VOUT vs VIN : gain, linear range, offset
* =====================================================================
.control
  dc VIN 0 1.2 0.005
  let gain   = deriv(v(VOUT))          ; dVOUT/dVIN, ~1 in the valid range
  let dcerr  = v(VOUT) - v(VIN)        ; follower error
  meas dc vout_at_vcm  FIND v(VOUT) WHEN v(VIN)=0.6
  meas dc gain_at_vcm  FIND gain      WHEN v(VIN)=0.6
  * write data for offline inspection / plotting
  wrdata dc_transfer.txt v(VOUT) gain dcerr
  * plot v(vout) v(vin)             ; uncomment for interactive view
  * plot gain
.endc

* =====================================================================
* 3) TRANSIENT  -  +/-100 mV step into the 1 uF load (slew + settling)
* =====================================================================
.control
  tran 1u 800u 0 1u
  meas tran vmin  MIN v(VOUT) FROM=100u TO=800u
  meas tran vmax  MAX v(VOUT) FROM=100u TO=800u
  * settle: time for VOUT to reach within 1 mV of the final 0.7 V step
  meas tran tsettle WHEN v(VOUT)=0.699 RISE=1
  wrdata tran_step.txt v(VIN) v(VOUT)
  * plot v(vin) v(vout)             ; uncomment for interactive view
.endc

* =====================================================================
* 4a) AC  -  closed-loop frequency response (gain flatness, -3 dB BW)
* =====================================================================
.control
  ac dec 20 1 1G
  let mag_db = db(v(VOUT))            ; VIN has AC=1, so this is the gain
  meas ac dcgain_db  FIND mag_db AT=10
  meas ac f3db       WHEN mag_db=-3.0103 FALL=1
  wrdata ac_gain.txt mag_db vp(VOUT)
  * plot mag_db                      ; uncomment for interactive view
.endc

* =====================================================================
* 4b) AC  -  closed-loop output impedance  Zout = v(VOUT)/i_inject
*     Drive VIN with DC only and push 1 A AC test current into VOUT.
*     (Re-runs with the probe enabled via an 'alter'.)
* =====================================================================
.control
  alter VIN  ac = 0
  alter IPROBE ac = 1
  ac dec 20 1 1G
  let zout = mag(v(VOUT))             ; |Zout| in ohms (1 A test current)
  meas ac zout_lf FIND zout AT=10     ; low-freq Zout, design target ~1 ohm
  wrdata ac_zout.txt zout
  * plot zout                        ; uncomment for interactive view
.endc

.end
