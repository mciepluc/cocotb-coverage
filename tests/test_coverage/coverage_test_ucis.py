# Copyright (c) 2019, TDK Electronics
# All rights reserved.
# 
# Author: Marek Cieplucha, https://github.com/mciepluc
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met (The BSD 2-Clause
# License):
# 
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Tests for the UCIS export feature.
"""

from cocotb_coverage import coverage
import random

def test_export_coverpoint():
    for i in range(13):
        x = random.randint(0, 3)

        @coverage.CoverPoint("top.t1.c1", vname="i", bins=list(range(6)))
        @coverage.CoverPoint("top.t1.c2", vname="x", bins=list(range(6)))
        @coverage.CoverPoint("top.t1.c3", vname="x", bins=list(range(6)), at_least=4)
        def sample(i, x):
            pass
    
        sample(i, x)

    # NOTE: run with "pytest -s" to see this:
    coverage.coverage_db.report_coverage(print, bins=True)

    coverage.coverage_db.export_to_ucis(filename="ucis_coverpoint.xml")


def test_export_covercheck():
    @coverage.CoverCheck(name = "top.t7.failed_check",
                         f_fail = lambda i : i == 0,
                         f_pass = lambda i : i > 5)
    @coverage.CoverCheck(name = "top.t7.passing_check",
                         f_fail = lambda i : i > 100,
                         f_pass = lambda i : i < 50)
    def sample(i):
        pass
    
    for i in range(5):
        sample(i)

    # NOTE: run with "pytest -s" to see this:
    coverage.coverage_db.report_coverage(print, bins=True)

    coverage.coverage_db.export_to_ucis(filename="ucis_covercheck.xml")
