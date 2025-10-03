# cocotb-coverage
Functional Coverage and Constrained Randomization Extensions for Cocotb

[![Documentation Status](https://readthedocs.org/projects/cocotb-coverage/badge/?version=latest)](http://cocotb-coverage.readthedocs.org/en/latest/)
[![Regression Tests](https://github.com/mciepluc/cocotb-coverage/actions/workflows/main.yml/badge.svg)](https://github.com/mciepluc/cocotb-coverage/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/dm/cocotb-coverage.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb-coverage/)

This package allows you to use constrained randomization and functional coverage techniques known from CRV (constrained random verification) and MDV (metric-driven verification) methodologies, available in SystemVerilog or _e_. Such extensions enable the implementation of an advanced verification environment for complex projects.

The implemented functionality is intended to be easily understandable by SystemVerilog users and provides significant extensions compared to Hardware Verification Languages.

There is an option to export coverage database to a readable XML or YML format and a function which allows for merging such files is provided.

### Installation
The package can be installed with pip. Version ```2.0.0``` is the latest one and recommended, adjusted for cocotb >= 2.0. 
For cocotb vesrions < 2.0, you may need to use ```1.2.0``` to get the examples and tests working. However, the core of cocotb-coverage is the same.
```
pip install cocotb-coverage
```

### References

* cocotb core package - [cocotb](https://github.com/potentialventures/cocotb)
* Constraint Solving Problem resolver used in this project - [python-constraint](https://github.com/python-constraint/python-constraint)
* [documentation](https://cocotb-coverage.readthedocs.io/en/latest/)
* [PyPI package](https://pypi.org/project/cocotb-coverage/)
* DVCon 2017 Paper - [New Constrained Random and MDV Methodology using Python](http://events.dvcon.org/2017/proceedings/papers/02_3.pdf)
* DVCon 2017 Presentation - [SLIDES](http://events.dvcon.org/2017/proceedings/slides/02_3.pdf)
* example advanced verification project - [apbi2c_cocotb_example](https://github.com/mciepluc/apbi2c_cocotb_example)

### Roadmap
* 2.0 released - 3 Oct 2025
* 1.2 released - 15 Nov 2023
* 1.1 released - 7 Aug 2020
* Planned basic support for UCIS coverage database format
* Any suggestions welcome - you are encouraged to open an issue!

### Code Example
```Python
# point represented by x and y coordinates in range (-10,10)
class Point(crv.Randomized):

    def __init__(self, x, y):
        crv.Randomized.__init__(self)
        self.x = x
        self.y = y

        self.add_rand("x", list(range(-10, 10)))
        self.add_rand("y", list(range(-10, 10)))
        # constraining the space so that x < y
        self.add_constraint(lambda x, y: x < y)

...

# create an arbitrary point
p = Point(0,0)

for _ in range (10):

    # cover example arithmetic properties
    @CoverPoint("top.x_negative", xf = lambda point : point.x < 0, bins = [True, False])
    @CoverPoint("top.y_negative", xf = lambda point : point.y < 0, bins = [True, False])
    @CoverPoint("top.xy_equal", xf = lambda point : point.x == point.y, bins = [True, False])
    @CoverCross("top.cross", items = ["top.x_negative", "top.y_negative"])
    def plot_point(point):
        ...

    p.randomize()  # randomize object
    plot_point(p)  # call a function which will sample the coverage

# export coverage to XML
coverage_db.export_to_xml(filename="coverage.xml")
# export coverage to YAML
coverage_db.export_to_yaml(filename="coverage.yml")
```
