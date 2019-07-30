
#Unit test may be called without cocotb package and hardware modules
#Just run it by:
#python -m pytest

MODULE = crv_test_main
TOPLEVEL := sample_module

TESTS_DIR = $(abspath $(dir $(abspath $(shell pwd))))

VERILOG_SOURCES = $(TESTS_DIR)/sample_module.sv

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
