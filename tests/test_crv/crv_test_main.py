
import cocotb
import pytest
import crv_test
from cocotb.triggers import Timer
from cocotb.result import TestFailure

@cocotb.test()
def test_crv(dut):
    exitcode = pytest.main()
    if exitcode != pytest.ExitCode.OK:
        raise TestFailure()
    yield Timer(1000)
