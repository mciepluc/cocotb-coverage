
import sys

__version__ = '2.0'

if sys.version_info[0] < 3:
    raise Exception("cocotb-coverage package requires Python 3")
