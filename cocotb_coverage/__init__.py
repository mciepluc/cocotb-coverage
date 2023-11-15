
import sys

__version__ = '1.2.1dev'

if sys.version_info[0] < 3:
    raise Exception("cocotb-coverage package requires Python 3")
