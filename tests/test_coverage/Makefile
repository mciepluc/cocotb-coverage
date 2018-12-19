
#Unit test may be called without cocotb package and hardware modules
#Just run it by:
#PYTHONPATH=../.. python coverage_unittest.py

PWD=$(shell pwd)

#Update your path to COCOTB package!
COCOTB=$(PWD)/../../../cocotb

#Path to cocotb-coverage
ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
PYTHONPATH := $(PWD)/../..;$(PYTHONPATH)
else
WPWD=$(shell pwd)
PYTHONPATH := $(PWD)/../..:$(PYTHONPATH)
endif

include $(COCOTB)/tests/designs/sample_module/Makefile

MODULE = test_coverage
