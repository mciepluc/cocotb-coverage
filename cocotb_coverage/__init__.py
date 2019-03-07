
import sys
if sys.version_info[0] < 3:
    raise Exception("cocotb-coverage package requies Python 3")

try:
    import constraint
except:
    raise Exception("You need to install python-constraint package")
