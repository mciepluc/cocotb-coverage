
'''Copyright (c) 2018, TDK Electronics
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
from cocotb_coverage import coverage

import unittest
import random

class TestCoverage(unittest.TestCase):

    #simple coverpoint
    def test_simple_coverpoint(self):
        print("Running test_simple_coverpoint")

        for i in range(10):
            x = random.randint(0,10)

            @coverage.CoverPoint("t1.c1", vname="i", bins = list(range(10)))
            @coverage.CoverPoint("t1.c2", vname="x", bins = list(range(10)))
            def sample(i, x):
                pass

            sample(i, x)

        #check coverage size
        self.assertTrue(coverage.coverage_db["t1.c1"].size == 10) 
        #expect all covered
        self.assertTrue(coverage.coverage_db["t1.c1"].coverage == 10)
        #expect 100%
        self.assertTrue(coverage.coverage_db["t1.c1"].cover_percentage == 100)
        #expect something covered
        self.assertTrue(0 < coverage.coverage_db["t1.c2"].coverage < 10)

        #expect each bin hit only once
        for i in range(10):
            self.assertTrue(coverage.coverage_db["t1.c1"].detailed_coverage[i] == 1)

        coverage.coverage_db.report_coverage(print, bins=False)

    class FooBar():
        def __init__(self):
            pass

        @coverage.CoverPoint("t2.in_class", bins = ["foo", "bar"])
        def cover(self, something):
            pass

    #coverpoint in class
    def test_coverpoint_in_class(self):
        print("Running test_coverpoint_in_class")            

        fb = self.FooBar()
        self.assertTrue(coverage.coverage_db["t2.in_class"].size == 2) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].coverage == 0) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["foo"] == 0) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["bar"] == 0) 
        fb.cover("bar")
        self.assertTrue(coverage.coverage_db["t2.in_class"].coverage == 1)
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["foo"] == 0) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["bar"] == 1) 
        fb.cover("bar")
        self.assertTrue(coverage.coverage_db["t2.in_class"].coverage == 1)
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["foo"] == 0) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["bar"] == 2)  
        fb.cover("foo")
        self.assertTrue(coverage.coverage_db["t2.in_class"].coverage == 2) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["foo"] == 1) 
        self.assertTrue(coverage.coverage_db["t2.in_class"].detailed_coverage["bar"] == 2) 
      

    #injective coverpoint - matching multiple bins at once
    def test_injective_coverpoint(self):
        print("Running test_injective_coverpoint")      

        def is_divider(number, divider):
            return number % divider == 0
      
        @coverage.CoverPoint("t3.inj", rel = is_divider, bins = [1, 2, 3, 5, 7, 11, 13, 17], inj = True)
        def sample(x):
            pass

        self.assertTrue(coverage.coverage_db["t3.inj"].size == 8) 
        self.assertTrue(coverage.coverage_db["t3.inj"].coverage == 0)  
        sample(17) #covers 1 and 17
        self.assertTrue(coverage.coverage_db["t3.inj"].coverage == 2) 
        sample(30) #covers 2,3 and 5
        self.assertTrue(coverage.coverage_db["t3.inj"].coverage == 5) 
        sample(77) #covers 7 and ``
        self.assertTrue(coverage.coverage_db["t3.inj"].coverage == 7) 

    #cross
    def test_covercross(self):
        print("Running test_covercross")

        for i in range(10):
            @coverage.CoverPoint("t4.c1", vname="x1", bins = list(range(10)))
            @coverage.CoverPoint("t4.c2", xf = lambda x1, x2, x3 : x2 ** (0.5), bins = list(range(10)))
            @coverage.CoverPoint("t4.c3", xf = lambda x1, x2, x3 : x1 + x2 + x3, bins = list(range(10)))
            @coverage.CoverCross("t4.cross1", items = ["t4.c1","t4.c2","t4.c3"])
            @coverage.CoverCross("t4.cross2", items = ["t4.c1","t4.c2"],
              ign_bins = [(None, 1), (2,2), (4, 5)] #ignored any c1 if c2=1, pair of (2,2) and (4,5)
              )
            @coverage.CoverCross("t4.cross3", items = ["t4.c1","t4.c2"],
              ign_bins = [(ii, ii) for ii in range(10)] #ignore all pairs of the same numbers
              )
            def sample(x1, x2, x3):
                pass

            sample(i, i**2, -i)

        #We expect c1 and c2 covered in all range, c3 covered bins: 0, 1, 4, 9
        self.assertTrue(coverage.coverage_db["t4.c1"].coverage == 10)
        self.assertTrue(coverage.coverage_db["t4.c2"].coverage == 10)
        self.assertTrue(coverage.coverage_db["t4.c3"].coverage == 4)
        #cross1 size is 1000 (10x10x10), but covered only 4 bins (note out of range)
        self.assertTrue(coverage.coverage_db["t4.cross1"].size == 1000)
        self.assertTrue(coverage.coverage_db["t4.cross1"].coverage == 4)
        #cross2 size is 100 (10x10) minus 12 = 88
        self.assertTrue(coverage.coverage_db["t4.cross2"].size == 88)
        self.assertTrue(coverage.coverage_db["t4.cross2"].coverage == 8)
        #cross3 size is 100 (10x10) minus 10 = 90
        self.assertTrue(coverage.coverage_db["t4.cross3"].size == 90)
        self.assertTrue(coverage.coverage_db["t4.cross3"].coverage == 0) #expect nothing covered


    #test at least and weight
    def test_at_least_and_weight(self):
        print("Running test_at_least_and_weight")

        @coverage.CoverPoint("t5.c1", vname="i", bins = list(range(10)), weight = 100)
        @coverage.CoverPoint("t5.c2", xf = lambda i, x : i % 6, bins = list(range(5)), at_least = 2)
        @coverage.CoverPoint("t5.c3", vname="x", bins = list(range(10)), at_least = 2)
        @coverage.CoverCross("t5.cross", items = ["t5.c1","t5.c2"], at_least = 2)
        def sample(i, x):
            pass

        for i in range(10):
            x = random.randint(0,5)
            sample(i, x)
 
        

        #expect all covered, but weight is * 100
        self.assertTrue(coverage.coverage_db["t5.c1"].size == 1000)
        self.assertTrue(coverage.coverage_db["t5.c1"].coverage == 1000)
        #in c2 expect covered only at least 2 times, so 4 in total
        self.assertTrue(coverage.coverage_db["t5.c2"].coverage == 4)
        #expect something covered in c3
        self.assertTrue(0 < coverage.coverage_db["t5.c3"].coverage < 10)
 
        self.assertTrue(coverage.coverage_db["t5.cross"].size == 50)
        self.assertTrue(coverage.coverage_db["t5.cross"].coverage == 0)
        sample(0, 0) #sample one more time to make sure cross satisfies "at_least" condition
        self.assertTrue(coverage.coverage_db["t5.cross"].coverage == 1)

    #test callbacks
    def test_callbacks(self):
        print("Running test_callbacks")

        current_step = 0
        cb1_fired = [False]
        cb2_fired = [False]
        cb3_fired = [False]

        def bins_callback_1():
            cb1_fired[0] = True
            print("Bins callback 1 fired at step %d" % current_step)
            self.assertTrue(current_step == 3 or current_step == 53)

        def threshold_callback_2():
            cb2_fired[0] = True
            print("Threshold callback 2 fired at step %d" % current_step)
            self.assertTrue(current_step == 49)

        def threshold_callback_3():
            cb3_fired[0] = True
            print("Threshold callback 3 fired at step %d" % current_step)
            self.assertTrue(current_step == 29)

        @coverage.CoverPoint("t6.c1", bins = list(range(100)))
        @coverage.CoverPoint("t6.c2", xf = lambda i : i % 50, bins = list(range(50)))
        def sample(i):
            pass

        coverage.coverage_db["t6.c1"].add_threshold_callback(threshold_callback_2,50)
        coverage.coverage_db["t6"].add_threshold_callback(threshold_callback_3,40)
        coverage.coverage_db["t6.c2"].add_bins_callback(bins_callback_1,3)

        for i in range(100):            
            sample(i)
            current_step += 1
 
        self.assertTrue(cb1_fired[0])
        self.assertTrue(cb2_fired[0])
        self.assertTrue(cb3_fired[0])

    #test xml export
    def test_xml(self):
        print("Running test_xml")
        coverage.coverage_db.export_to_xml(xml_name='coverage_test')
        
if __name__ == '__main__':
    import sys
    print("PYTHON VERSION: ", sys.version)
    unittest.main()
