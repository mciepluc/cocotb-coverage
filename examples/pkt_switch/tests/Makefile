TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

VERILOG_SOURCES = $(PWD)/../hdl/pkt_switch.v
TOPLEVEL := pkt_switch
MODULE   := test_pkt_switch

include $(shell cocotb-config --makefiles)/Makefile.sim
