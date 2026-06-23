# cocotb regression for the digital reference block.
# Default simulator is Icarus Verilog (free, apt-installable).
#   make            # run the test
#   make clean      # remove sim artifacts

SIM           ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += $(realpath ../rtl/boxcar_filter.v)

TOPLEVEL = boxcar_filter
MODULE   = test_boxcar_filter

include $(shell cocotb-config --makefiles)/Makefile.sim
