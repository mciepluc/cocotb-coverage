import cocotb
import pytest
import coverage_test
from cocotb.triggers import Timer
from cocotb.result import TestFailure

@cocotb.test()
def coverage_test_main(dut):
    exitcode = pytest.main()
    if exitcode != pytest.ExitCode.OK:
        raise TestFailure()
    yield Timer(1000)