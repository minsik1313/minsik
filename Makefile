# MTU (Minsik Tensor Unit) build & verification entry points.
#
#   make test     -- build + run all cocotb testbenches (Icarus Verilog)
#   make pe / systolic / top  -- run a single testbench
#   make lint     -- Verilator lint of the full RTL
#   make clean    -- remove simulation build artifacts

PY      ?= python3
RTL     := rtl/pe/pe.sv rtl/mxu/systolic_array.sv rtl/mtu_top.sv

.PHONY: test pe systolic top lint clean

test:
	$(PY) sim.py

pe:
	$(PY) sim.py pe

systolic:
	$(PY) sim.py systolic_array

top:
	$(PY) sim.py mtu_top

lint:
	verilator --lint-only -Wall -Wno-DECLFILENAME --timing \
		$(RTL) --top-module mtu_top

clean:
	rm -rf sim_build results.xml
