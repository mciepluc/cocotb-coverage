
import cocotb
import unittest
import coverage_unittest
from cocotb.triggers import Timer

@cocotb.test()
def test_coverage(dut):
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromModule(coverage_unittest))
    unittest.TextTestRunner().run(suite)
    yield Timer(1000)
