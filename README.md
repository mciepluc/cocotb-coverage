# cocotb-coverage
Functional Coverage and Constrained Randomization Extensions for Cocotb

[![Documentation Status](https://readthedocs.org/projects/cocotb-coverage/badge/?version=latest)](http://cocotb-coverage.readthedocs.org/en/latest/)
[![Build Status](https://travis-ci.org/mciepluc/cocotb-coverage.svg?branch=master)](https://travis-ci.org/mciepluc/cocotb-coverage)
[![PyPI](https://img.shields.io/pypi/dm/cocotb-coverage.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb-coverage/)

This package allows you to use constrained randomization and functional coverage techniques known from CRV (constrained random verification) and MDV (metric-driven verification) methodologies, available in SystemVerilog or _e_. Such extensions enable the implementation of an advanced verification environment for complex projects.

The implemented functionality is intended to be easily understandable by SystemVerilog users and provides significant extensions compared to Hardware Verification Languages. 

There is an option to export coverage database to a readable XML format and a function which allows for merging such files is provided. 

References:
* cocotb core package - [cocotb](https://github.com/potentialventures/cocotb)
* Constraint Solving Problem resolver used in this project - [python-constraint](https://github.com/python-constraint/python-constraint)
* [documentation](https://cocotb-coverage.readthedocs.io/en/latest/) 
* [PyPI package](https://pypi.org/project/cocotb-coverage/)
* DVCon 2017 Paper - [New Constrained Random and MDV Methodology using Python](http://events.dvcon.org/2017/proceedings/papers/02_3.pdf)
* DVCon 2017 Presentation - [SLIDES](http://events.dvcon.org/2017/proceedings/slides/02_3.pdf)
* example advanced verification project - [apbi2c_cocotb_example](https://github.com/mciepluc/apbi2c_cocotb_example)

Simple example below:
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

#export coverage to XML
coverage_db.export_to_xml(xml_name="coverage.xml")
              
```
