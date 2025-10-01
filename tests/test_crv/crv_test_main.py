
import cocotb
import pytest
import crv_test
from cocotb.triggers import Timer

@cocotb.test()
async def test_crv(dut):
    exitcode = pytest.main()
    assert exitcode == pytest.ExitCode.OK
    await Timer(1000)
