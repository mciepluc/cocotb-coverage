
'''Copyright (c) 2019, TDK Electronics
All rights reserved.

Author: Marek Cieplucha, https://github.com/mciepluc

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met (The BSD 2-Clause 
License):

1. Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation and/or 
other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
Constrained-random verification features unittest.
"""
from cocotb_coverage import crv
from cocotb_coverage import coverage

import pytest

class SimpleRandomized(crv.Randomized):

    def __init__(self, x, y):
        crv.Randomized.__init__(self)
        self.x = x
        self.y = y
        self.size = "small"

        self.add_rand("x", list(range(0, 10)))
        self.add_rand("y", list(range(0, 10)))
        self.add_rand("size", ["small", "medium", "large"])

        self.add_constraint(lambda x, y: x < y)

#simple randomization - test if simple constraint works and if all 
#possible SimpleRandomize.size values picked
def test_simple_0():
    print("Running test_simple_0")
    
    size_hits = []
    for _ in range(20):
        a = SimpleRandomized(0, 0)
        a.randomize()
        assert a.x < a.y
        size_hits.append(a.size)
    assert [x in size_hits for x in["small", "medium", "large"]] == [True, True, True]

class RandomizedTrasaction(crv.Randomized):

    def __init__(self, address, data=0, write=False, delay=1):
        crv.Randomized.__init__(self)
        self.addr = address
        self.data = data
        self.write = write
        self.delay1 = delay
        self.delay2 = 0
        self.delay3 = 0

        if data is None:
            self.add_rand("data")

        self.add_rand("delay1", list(range(10)))
        self.add_rand("delay2", list(range(10)))
        self.add_rand("delay3", list(range(10)))
        
        c1 = lambda delay1, delay2: delay1 <= delay2
        d1 = lambda delay1, delay2: 0.9 if (delay2 < 5) else 0.1
        d2 = lambda addr, delay1: 0.5 * delay1 if (addr == 5) else 1
        d3 = lambda delay1: 0.7 if (delay1 < 5) else 0.3
        c2 = lambda addr, data: data < 10000 if (addr == 0) else data < 5000
        
        self.add_constraint(c1)
        self.add_constraint(c2)
        self.add_constraint(d1)
        self.add_constraint(d2)
        self.add_constraint(d3)

#test if several constraints met at once
def test_simple_1():
    print("Running test_simple_1")
    for i in range(10):
        x = RandomizedTrasaction(i, data=None)
        x.randomize()
        assert x.delay1 <= x.delay2
        assert x.data <= 10000
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))

#test if randomize_with() is replacing existing constraint c1
def test_randomize_with():
    print("Running test_randomize_with")
    for i in range(10):
        x = RandomizedTrasaction(i, data=None)
        x.randomize_with(lambda delay1, delay2: delay1 == delay2 - 1)
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))
        assert (x.delay2 - x.delay1) == 1
        assert x.data <= 10000

#test if additional constraints can be added to the randomized objects
def test_adding_constraints():
    print("Running test_adding_constraints")

    c3 = lambda data, delay1: 0 if (data < 10) else 1
    c4 = lambda data, delay3: 0.5 * delay3 if (data < 20) else 2 * delay3
    c5 = lambda data: data < 50

    for i in range(5):
        x = RandomizedTrasaction(i, data=None)
        x.add_constraint(c3)
        x.add_constraint(c4)
        x.add_constraint(c5)
        x.randomize()
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))
        assert x.delay1 <= x.delay2 # check if c1 still works
        assert x.data < 50  # check if c5 applies
        assert x.data >= 10  # check if c3 applies

#test if a constraint may be added an then deleted
def test_deleting_constraints():
    print("Running test_deleting_constraints")

    c3 = lambda data: data < 50

    for i in range(5):
        x = RandomizedTrasaction(i, data=None)
        x.add_constraint(c3)
        x.randomize()
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))
        assert x.delay1 <= x.delay2 # check if c1 still works
        assert x.data < 50 # check if c3 applies
        x.del_constraint(c3) 
        x.randomize()
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))
        assert x.delay1 <= x.delay2 # check if c1 still works
        assert x.data > 50 # check if c3 deleted

#test if solve_order function works          
def test_solve_order():
    print("Running test_solve_order")

    for i in range(10):
        x = RandomizedTrasaction(i, data=None)
        x.solve_order("delay1", ["delay2", "delay3"])
        x.randomize()
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))
        assert x.delay1 <= x.delay2 # check if c1 satisfied
 
#test exception throw when overconstraint occurs      
def test_cannot_resolve():
    print("Running test_cannot_resolve")

    c3 = lambda delay2, delay3: delay3 > delay2
    c4 = lambda delay1: delay1 == 9

    for i in range(10):
        x = RandomizedTrasaction(i, data=None)
        x.add_constraint(c3)
        x.add_constraint(c4)
        try: #we expect excpetion to be thrown each time
            x.randomize()
            assert 0 
        except Exception:
            assert 1     
 
#test solutions with zero probability            
def test_zero_probability():
    print("Running test_zero_probability")

    d4 = lambda delay2: 0 if delay2 < 10 else 1

    for i in range(10):
        x = RandomizedTrasaction(i, data=None)
        x.add_constraint(d4)
        x.randomize()
        print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
              (x.delay1, x.delay2, x.delay3, x.data))  
        assert x.delay2 == 0 #check if d4 applies

class RandomizedDist(crv.Randomized):

    def __init__(self, limit, n):
        crv.Randomized.__init__(self)
        self.x = 0
        self.y = 0
        self.z = 0
        self.n = n
        self.e_pr = False

        self.add_rand("x", list(range(limit)))
        self.add_rand("y", list(range(limit)))
        self.add_rand("z", list(range(limit)))
        
    def post_randomize(self):
        if self.e_pr:
            self.n = self.x + self.y + self.z + self.n

#test distributions
def test_distributions_1():
    print("Running test_distributions_1")

    d1 = lambda x: 20 / (x + 1)
    d2 = lambda y: 2 * y
    d3 = lambda n, z: n * z

    x_gr_y = 0

    for i in range(1, 10):
        foo = RandomizedDist(limit=20 * i, n=i - 1)
        foo.add_constraint(d1)
        foo.add_constraint(d2)
        foo.add_constraint(d3)
        foo.randomize()
        print("x = %d, y = %d, z = %d, n = %d" %
              (foo.x, foo.y, foo.z, foo.n))
        x_gr_y = x_gr_y + 1 if (foo.x > foo.y) else x_gr_y - 1
        if (i == 1):
            # z should not be randomised as has 0 probability for each
            # solution
            assert foo.z == 0

    # x should be less than y most of the time due to decreasing
    # probability density distribution
    assert x_gr_y < 0

#test coverage
def test_cover():
    print("Running test_cover")
    n = 5

    cover = coverage.coverage_section(
        coverage.CoverPoint(
            "top.c1", xf=lambda x: x.x, bins=list(range(10))),
        coverage.CoverPoint(
            "top.c2", xf=lambda x: x.y, bins=list(range(10))),
        coverage.CoverCheck("top.check", f_fail=lambda x: x.n != n)
    )

    @cover
    def sample(x):
        print("x = %d, y = %d, z = %d, n = %d" %
              (foo.x, foo.y, foo.z, foo.n))

    for _ in range(10):
        foo = RandomizedDist(10, n)
        foo.randomize()
        sample(foo)

    coverage_size = coverage.coverage_db["top"].size
    coverage_level = coverage.coverage_db["top"].coverage

    assert coverage_level > coverage_size / 2  # expect >50%
    
#test if post_randomize works
def test_post_randomize():
    print("Running test_post_randomize")

    n = 5
    foo = RandomizedDist(10, n)
    foo.e_pr = True #enable post-randomize
    for _ in range(5):
        foo.randomize()
        print("x = %d, y = %d, z = %d, n = %d" %
              (foo.x, foo.y, foo.z, foo.n))
        
    assert foo.n > 5

def test_issue28():
    print("Test issue28")

    class Foo(crv.Randomized):
        def __init__(self):
            crv.Randomized.__init__(self)
            self.dac_max = 0
            self.dac_min = 0

            self.add_rand("dac_max",         list(range(16)))
            self.add_rand("dac_min",         list(range(16)))
            self.add_constraint(lambda dac_max, dac_min : dac_max > dac_min   )

    foo = Foo()

    for _ in range(5):
        #foo.randomize()
        #assert foo.dac_max > foo.dac_min
        foo.randomize_with(lambda dac_max : dac_max == 8)
        assert foo.dac_max == 8
        assert foo.dac_max > foo.dac_min
        foo.randomize_with(lambda dac_max : dac_max == 8, lambda dac_min : dac_min == 2)
        assert foo.dac_max == 8
        assert foo.dac_min == 2

def test_issue27():
    print("Test issue27")

    exception_fired = [False]

    class Foo(crv.Randomized):
        def __init__(self):
            crv.Randomized.__init__(self)
            self.x = 0
            self.y = 0

            self.add_rand("x")
            try:
               self.add_rand("y ")
            except:
               exception_fired[0] = True

    foo = Foo()
    assert exception_fired[0]

