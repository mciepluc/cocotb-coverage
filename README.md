# cocotb-coverage
Functional Coverage and Constrained Randomization Extensions for Cocotb

This package allows you to use constrained randomization and functional coverage techniques known from CRV (constrained random verification) and MDV (metric-driven verification) methodologies, available in SystemVerilog or _e_. Such extensions enable implementation of the advanced verification environment for complex projects.

The implemented funcionality was intended to be well-undertood by SystemVerilog users and provides significant extensions compared to Hardware Verification Languages. 

References:
* Cocotb Core Package - [cocotb](https://github.com/potentialventures/cocotb)
* DVCon 2017 Paper - [New Constrained Random and MDV Methodology using Python](http://events.dvcon.org/2017/proceedings/papers/02_3.pdf)
* DVCon 2017 Presentation - [SLIDES](http://events.dvcon.org/2017/proceedings/slides/02_3.pdf)
* Example Advanced Project - [APB_I2C Cocotb Example](https://github.com/mciepluc/apbi2c_cocotb_example)

Simple example below:
```Python
#point represented by x and y coordinates in range (-10,10)
class Point(crv.Randomized):

    def __init__(self, x, y):
        crv.Randomized.__init__(self)
        self.x = x
        self.y = y

        self.addRand("x", list(range(-10, 10)))
        self.addRand("y", list(range(-10, 10)))
        #constraining the space such as x < y
        self.addConstraint(lambda x, y: x < y)

...

#create an arbitrary point
p = Point(0,0)

for _ in range (10):
    
    #cover example arithmetic properties
    @CoverPoint("top.x_negative", xf = lambda point : point.x < 0, bins = [True, False])
    @CoverPoint("top.y_negative", xf = lambda point : point.y < 0, bins = [True, False])
    @CoverPoint("top.xy_equal", xf = lambda point : point.x == point.y, bins = [True, False])
    @CoverCross("top.cross", items = ["top.x_negative", "top.y_negative"])
    def plot_point(point):
        ...
    
    p.randomize() #randomize object
    plot_point(p) #call a function which will sample the coverage
              
```
