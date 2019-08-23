
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

from cocotb_coverage import coverage

import pytest
import random


#simple coverpoint
def test_simple_coverpoint():
    print("Running test_simple_coverpoint")

    for i in range(10):
        x = random.randint(0,10)

        @coverage.CoverPoint("top.t1.c1", vname="i", bins = list(range(10)))
        @coverage.CoverPoint("top.t1.c2", vname="x", bins = list(range(10)))
        def sample(i, x):
            pass

        sample(i, x)

    #check coverage size
    assert coverage.coverage_db["top.t1.c1"].size == 10
    #expect all covered
    assert coverage.coverage_db["top.t1.c1"].coverage == 10
    #expect 100%
    assert coverage.coverage_db["top.t1.c1"].cover_percentage == 100
    #expect something covered
    assert 0 < coverage.coverage_db["top.t1.c2"].coverage < 10

    #expect each bin hit only once
    for i in range(10):
        assert coverage.coverage_db["top.t1.c1"].detailed_coverage[i] == 1

    #coverage.coverage_db.report_coverage(print, bins=False)

class FooBar():
    def __init__(self):
        pass

    @coverage.CoverPoint("top.t2.in_class", bins = ["foo", "bar"])
    def cover(self, something):
        pass

#coverpoint in class
def test_coverpoint_in_class():
    print("Running test_coverpoint_in_class")            

    fb = FooBar()
    assert coverage.coverage_db["top.t2.in_class"].size == 2 
    assert coverage.coverage_db["top.t2.in_class"].coverage == 0 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["foo"] == 0 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["bar"] == 0 
    fb.cover("bar")
    assert coverage.coverage_db["top.t2.in_class"].coverage == 1
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["foo"] == 0 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["bar"] == 1 
    fb.cover("bar")
    assert coverage.coverage_db["top.t2.in_class"].coverage == 1
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["foo"] == 0 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["bar"] == 2  
    fb.cover("foo")
    assert coverage.coverage_db["top.t2.in_class"].coverage == 2 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["foo"] == 1 
    assert coverage.coverage_db["top.t2.in_class"].detailed_coverage["bar"] == 2 
  

#injective coverpoint - matching multiple bins at once
def test_injective_coverpoint():
    print("Running test_injective_coverpoint")      

    def is_divider(number, divider):
        return number % divider == 0
  
    @coverage.CoverPoint("top.t3.inj", rel = is_divider, bins = [1, 2, 3, 5, 7, 11, 13, 17], inj = True)
    def sample(x):
        pass

    assert coverage.coverage_db["top.t3.inj"].size == 8 
    assert coverage.coverage_db["top.t3.inj"].coverage == 0  
    sample(17) #covers 1 and 17
    assert coverage.coverage_db["top.t3.inj"].coverage == 2 
    sample(30) #covers 2,3 and 5
    assert coverage.coverage_db["top.t3.inj"].coverage == 5 
    sample(77) #covers 7 and 11
    assert coverage.coverage_db["top.t3.inj"].coverage == 7 

#cross
def test_covercross():
    print("Running test_covercross")

    for i in range(10):
        @coverage.CoverPoint("top.t4.c1", vname="x1", bins = list(range(10)))
        @coverage.CoverPoint("top.t4.c2", xf = lambda x1, x2, x3 : x2 ** (0.5), bins = list(range(10)))
        @coverage.CoverPoint("top.t4.c3", xf = lambda x1, x2, x3 : x1 + x2 + x3, bins = list(range(10)))
        @coverage.CoverCross("top.t4.cross1", items = ["top.t4.c1","top.t4.c2","top.t4.c3"])
        @coverage.CoverCross("top.t4.cross2", items = ["top.t4.c1","top.t4.c2"],
          ign_bins = [(None, 1), (2,2), (4, 5)] #ignored any c1 if c2=1, pair of (2,2) and (4,5)
          )
        @coverage.CoverCross("top.t4.cross3", items = ["top.t4.c1","top.t4.c2"],
          ign_bins = [(ii, ii) for ii in range(10)] #ignore all pairs of the same numbers
          )
        def sample(x1, x2, x3):
            pass

        sample(i, i**2, -i)

    #We expect c1 and c2 covered in all range, c3 covered bins: 0, 1, 4, 9
    assert coverage.coverage_db["top.t4.c1"].coverage == 10
    assert coverage.coverage_db["top.t4.c2"].coverage == 10
    assert coverage.coverage_db["top.t4.c3"].coverage == 4
    #cross1 size is 1000 (10x10x10), but covered only 4 bins (note out of range)
    assert coverage.coverage_db["top.t4.cross1"].size == 1000
    assert coverage.coverage_db["top.t4.cross1"].coverage == 4
    #cross2 size is 100 (10x10) minus 12 = 88
    assert coverage.coverage_db["top.t4.cross2"].size == 88
    assert coverage.coverage_db["top.t4.cross2"].coverage == 8
    #cross3 size is 100 (10x10) minus 10 = 90
    assert coverage.coverage_db["top.t4.cross3"].size == 90
    assert coverage.coverage_db["top.t4.cross3"].coverage == 0 #expect nothing covered


#test at least and weight
def test_at_least_and_weight():
    print("Running test_at_least_and_weight")

    @coverage.CoverPoint("top.t5.c1", vname="i", bins = list(range(10)), weight = 100)
    @coverage.CoverPoint("top.t5.c2", xf = lambda i, x : i % 6, bins = list(range(5)), at_least = 2)
    @coverage.CoverPoint("top.t5.c3", vname="x", bins = list(range(10)), at_least = 2)
    @coverage.CoverCross("top.t5.cross", items = ["top.t5.c1","top.t5.c2"], at_least = 2)
    def sample(i, x):
        pass

    for i in range(10):
        x = random.randint(0,5)
        sample(i, x)

    #expect all covered, but weight is * 100
    assert coverage.coverage_db["top.t5.c1"].size == 1000
    assert coverage.coverage_db["top.t5.c1"].coverage == 1000
    #in c2 expect covered only at least 2 times, so 4 in total
    assert coverage.coverage_db["top.t5.c2"].coverage == 4
    #expect something covered in c3
    assert 0 < coverage.coverage_db["top.t5.c3"].coverage < 10

    assert coverage.coverage_db["top.t5.cross"].size == 50
    assert coverage.coverage_db["top.t5.cross"].coverage == 0
    sample(0, 0) #sample one more time to make sure cross satisfies "at_least" condition
    assert coverage.coverage_db["top.t5.cross"].coverage == 1

#test callbacks
def test_callbacks():
    print("Running test_callbacks")

    current_step = 0
    cb1_fired = [False]
    cb2_fired = [False]
    cb3_fired = [False]

    def bins_callback_1():
        cb1_fired[0] = True
        print("Bins callback 1 fired at step %d" % current_step)
        assert current_step == 3 or current_step == 53

    def threshold_callback_2():
        cb2_fired[0] = True
        print("top.threshold callback 2 fired at step %d" % current_step)
        assert current_step == 49

    def threshold_callback_3():
        cb3_fired[0] = True
        print("top.threshold callback 3 fired at step %d" % current_step)
        assert current_step == 29

    @coverage.CoverPoint("top.t6.c1", bins = list(range(100)))
    @coverage.CoverPoint("top.t6.c2", xf = lambda i : i % 50, bins = list(range(50)))
    def sample(i):
        pass

    coverage.coverage_db["top.t6.c1"].add_threshold_callback(threshold_callback_2,50)
    coverage.coverage_db["top.t6"].add_threshold_callback(threshold_callback_3,40)
    coverage.coverage_db["top.t6.c2"].add_bins_callback(bins_callback_1,3)

    for i in range(100):            
        sample(i)
        current_step += 1

    assert cb1_fired[0]
    assert cb2_fired[0]
    assert cb3_fired[0]

#test xml export
def test_xml_export():
    import os.path
    from xml.etree import ElementTree as et
    import yaml
    print("Running test_xml_export")
    
    #test CoverCheck
    @coverage.CoverCheck(name = "top.t7.failed_check", 
                         f_fail = lambda i : i == 0, 
                         f_pass = lambda i : i > 5)
    @coverage.CoverCheck(name = "top.t7.passing_check", 
                         f_fail = lambda i : i > 100, 
                         f_pass = lambda i : i < 50)
    def sample(i):
        pass
    
    for i in range(50):            
        sample(i)
        
    #coverage.coverage_db.report_coverage(print, bins=False)
    
    #Export coverage to XML, check if file exists
    xml_filename = 'test_xml_export_output.xml'
    yml_filename = 'test_yaml_export_output.yml'
    coverage.coverage_db.export_to_xml(filename='test_xml_export_output.xml')
    coverage.coverage_db.export_to_yaml(filename='test_yaml_export_output.yml')
    assert os.path.isfile(xml_filename)
    assert os.path.isfile(yml_filename)
    
    #Read back the XML           
    xml_db = et.parse(xml_filename).getroot()
    #dict - child: [all parents for that name]
    child_parent_dict = {} 
    for p in xml_db.iter():
        for c in p:
            if 'bin' not in c.tag:
                if c.tag not in child_parent_dict.keys():
                    child_parent_dict[c.tag] = [p.tag]
                else:
                    child_parent_dict[c.tag].append(p.tag)
     
    #Check if coverage_db items are XML, with proper parents
    for item in coverage.coverage_db:
        if '.' in item:
            item_elements = item.split('.')
            assert 'top' in child_parent_dict[item_elements[1]]
            for elem_parent, elem in zip(item_elements, item_elements[1:]):
                assert elem_parent in child_parent_dict[elem]

    #Check YML
    yml_db = yaml.full_load(open(yml_filename, 'r'))
    for item in yml_db:
        if isinstance(coverage.coverage_db[item], coverage.CoverPoint):
            #assert if correct coverage levels
            assert yml_db[item]['coverage'] == coverage.coverage_db[item].coverage

    #check if yaml and coverage databases have equal size
    assert len(yml_db) == len(coverage.coverage_db) 

# test xml merge - static example covering 
# adding new elements and updating existing
def test_xml_merge():
    import os.path
    from xml.etree import ElementTree as et
    print("Running test_xml_merge")
    filename = 'test_xml_merge_output.xml'

    coverage.XML_merger(filename, 'short1.xml', 'short2.xml', 'short3.xml')
    assert os.path.isfile(filename)
    
    #Read back the XML           
    xml_db = et.parse(filename).getroot()
    assert xml_db.tag == 'top'
    assert xml_db.attrib['coverage'] == '102'
    assert xml_db.attrib['size'] == '104'


#test covercheck
def test_covercheck():
    print("Running test_covercheck")

    @coverage.CoverCheck("top.t8.check", f_pass = lambda x : x > 0, f_fail = lambda x : x < 0, at_least = 2)
    def sample(x):
        pass 

    assert coverage.coverage_db["top.t8.check"].size == 1 
    assert coverage.coverage_db["top.t8.check"].coverage == 0 
    sample(0)
    sample(1)
    assert coverage.coverage_db["top.t8.check"].coverage == 0 #should not be covered yet
    sample(5)
    assert coverage.coverage_db["top.t8.check"].coverage == 1 #should be covered now
    sample(-1)
    assert coverage.coverage_db["top.t8.check"].coverage == 0 #should be fixed 0 now forever
    sample(4)
    sample(3)
    sample(1)
    assert coverage.coverage_db["top.t8.check"].coverage == 0
    sample(-1)
    assert coverage.coverage_db["top.t8.check"].coverage == 0

def test_print_coverage():
    print("Running test_print_coverage")

    @coverage.CoverPoint("top.t9.c1", bins=[1,2,3])
    def sample(i):
        pass

    print_ = []
    def logger(_):
        print_.append(_)

    coverage.coverage_db.report_coverage(logger, bins=True, node="top.t9")

    #check if only t9 printed
    #print(print_)
    assert print_[0].strip().startswith("top.t9")
    

def test_bins_labels():
    print("Running test_bins_labels")

    @coverage.CoverPoint("top.t10.c1", xf = lambda i,j : (i , i), bins_labels = ["a", "b"], bins=[(1,1), (2,2)])
    @coverage.CoverPoint("top.t10.c2", vname="j", bins_labels = ["c", "d"], bins=[3,4])
    @coverage.CoverCross("top.t10.cross", items=["top.t10.c1", "top.t10.c2"])
    def sample(i,j):
        pass

    assert coverage.coverage_db["top.t10.cross"].size == 4
    sample(1,1)
    assert coverage.coverage_db["top.t10.cross"].coverage == 0
    sample(1,3)
    assert coverage.coverage_db["top.t10.cross"].coverage == 1
    sample(1,4)
    assert coverage.coverage_db["top.t10.cross"].coverage == 2
    sample(2,4)
    assert coverage.coverage_db["top.t10.cross"].coverage == 3
    sample(2,3)
    assert coverage.coverage_db["top.t10.cross"].coverage == 4


