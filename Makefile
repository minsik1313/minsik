# Top-level orchestration for the open-source fabless flow.
# See docs/FABLESS_PLAN.md and docs/SETUP.md.

.PHONY: help digital-sim analog-autosize digital-gds clean

help:
	@echo "Targets:"
	@echo "  make digital-sim     - cocotb regression on the digital block (needs iverilog, cocotb)"
	@echo "  make analog-autosize - voltage-domain-aware analog sizing (needs ngspice)"
	@echo "  make digital-gds     - hint for the OpenLane2 RTL->GDS run"
	@echo "  make clean           - remove simulation artifacts"

digital-sim:
	$(MAKE) -C digital/tb

analog-autosize:
	python3 analog/sizing/autosize.py

digital-gds:
	@echo "Run inside IIC-OSIC-TOOLS: openlane digital/openlane/config.json (needs OpenLane2 + sky130A)"

clean:
	-$(MAKE) -C digital/tb clean
