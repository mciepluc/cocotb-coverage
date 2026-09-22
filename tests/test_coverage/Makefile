
#Unit test may be called without cocotb package and hardware modules
#Just run it by:
#python -m pytest

COCOTB_TEST_MODULES = coverage_test_main
COCOTB_TOPLEVEL := sample_module
export COCOTB_RANDOM_SEED := 0

TESTS_DIR = $(abspath $(dir $(abspath $(shell pwd))))

VERILOG_SOURCES = $(TESTS_DIR)/sample_module.sv

include $(shell cocotb-config --makefiles)/Makefile.sim
