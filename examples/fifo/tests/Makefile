TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

#Update your path to COCOTB package!
COCOTB=$(PWD)/../../../../cocotb

#Path to cocotb-coverage
ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
PYTHONPATH := $(PWD)/../../..;$(PYTHONPATH)
else
WPWD=$(shell pwd)
PYTHONPATH := $(PWD)/../../..:$(PYTHONPATH)
endif

VERILOG_SOURCES = $(PWD)/../hdl/fifo.v
TOPLEVEL := fifo_mem
MODULE   := test_fifo

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
