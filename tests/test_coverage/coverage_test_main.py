import cocotb
import pytest
import coverage_test
from cocotb.triggers import Timer

@cocotb.test()
def coverage_test_main(dut):
    exitcode = pytest.main()
    assert exitcode == pytest.ExitCode.OK
    yield Timer(1000)
