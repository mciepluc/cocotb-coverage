
import cocotb
import pytest
import crv_test
from cocotb.triggers import Timer

@cocotb.test()
def test_crv(dut):
    exitcode = pytest.main()
    assert exitcode == pytest.ExitCode.OK
    yield Timer(1000)
