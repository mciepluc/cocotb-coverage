
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
Example FIFO testbench with functional coverage.
Simple FIFO is tested by randomly writing/reading data.
The verification goal is to test data consistency, given that FIFO may be in
different states. No data is accepted when FIFO is full and no data can be read 
when FIFO is empty. Testbench checks FIFO operations in all such conditions. 
Data consistency is checked with FIFO model (double-ended queue).
"""

import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly

from cocotb_coverage.coverage import *

from collections import deque

import random

class FifoStatus():
    """
    Object representing FIFO status (full/empty etc.) 
    """
    def __init__(self, dut):
        self.dut = dut
    
    @cocotb.coroutine   
    def update(self):
        yield ReadOnly()
        self.empty = (self.dut.fifo_empty == 1)
        self.full = (self.dut.fifo_full == 1)
        self.threshold = (self.dut.fifo_threshold == 1)
        self.overflow = (self.dut.fifo_overflow == 1)
        self.underflow = (self.dut.fifo_underflow == 1)
       
#functional coverage - check if all FIFO states have been reached
#and check if read or write operation performed in every FIFO state 
FIFO_Coverage = coverage_section (
  CoverPoint("top.rw", xf = lambda data, rw, status : rw, bins = [True, False]),
  CoverPoint("top.fifo_empty", xf = lambda data, rw, status : status.empty, bins = [True, False]),
  CoverPoint("top.fifo_full", xf = lambda data, rw, status : status.full, bins = [True, False]),
  CoverPoint("top.fifo_threshold", xf = lambda data, rw, status : status.threshold, bins = [True, False]),
  CoverPoint("top.fifo_overflow", xf = lambda data, rw, status : status.overflow, bins = [True, False]),
  CoverPoint("top.fifo_underflow", xf = lambda data, rw, status : status.underflow, bins = [True, False]),
  CoverCross("top.rwXempty", items = ["top.rw", "top.fifo_empty"]),
  CoverCross("top.rwXfull", items = ["top.rw", "top.fifo_full"]),
  CoverCross("top.rwXthreshold", items = ["top.rw", "top.fifo_threshold"]),
  CoverCross("top.rwXoverflow", items = ["top.rw", "top.fifo_overflow"]),
  CoverCross("top.rwXunderflow", items = ["top.rw", "top.fifo_underflow"]) 
)

#simple clock generator
@cocotb.coroutine
def clock_gen(signal, period=10000):
    while True:
        signal <= 0
        yield Timer(period/2)
        signal <= 1
        yield Timer(period/2)

@cocotb.test()
def fifo_test(dut):
    """ FIFO Test """
    
    log = cocotb.logging.getLogger("cocotb.test") #logger instance
    cocotb.fork(clock_gen(dut.clk, period=100)) #start clock running
    
    fifo_model = deque() #simple scoreboarding - FIFO model as double-ended queue
    
    #reset & init
    dut.rst_n <= 1
    dut.wr <= 0
    dut.rd <= 0
    dut.data_in <= 0
    
    yield Timer(1000)
    dut.rst_n <= 0
    yield Timer(1000)
    dut.rst_n <= 1
    
    #procedure of processing data (FIFO logic)
    #coverage sampled here - at each function call
    @FIFO_Coverage
    @cocotb.coroutine
    def process_data(data, rw, status):
        success = True
        if rw: #read
            yield RisingEdge(dut.clk)
            #even if fifo empty, try to access in order to reach underflow status
            if (status.empty): 
                success = False
            else:
                data = int(dut.data_out)
            dut.rd <= 1
            yield RisingEdge(dut.clk)
            dut.rd <= 0  
        elif not rw:   
            yield RisingEdge(dut.clk)
            dut.data_in <= data
            dut.wr <= 1
            yield RisingEdge(dut.clk)
            dut.wr <= 0    
            #if FIFO full, data was not written (overflow status)
            if status.full:
                success = False        
        return data, success  
          
    status = FifoStatus(dut) #create FifoStatus object
        
    #main loop
    for _ in range(100): #is that enough repetitions to ensure coverage goal? Check out!
        rw = random.choice([True, False])
        data = random.randint(0,255) if not rw else None
        
        #call coroutines
        yield status.update() #check FIFO state
        #process data, and check if succeded
        data, success = yield process_data(data, rw, status)
        
        if rw: #read
            if success:
                #if successful read, check read data with the model
                assert(data == fifo_model.pop()) 
                log.info("Data read from fifo: %X", data)  
            else:
                log.info("Data NOT read, fifo EMPTY!") 
        else: #write
            if success:
                #if successful write, append written data to the model
                fifo_model.appendleft(data) 
                log.info("Data written to fifo: %X", data)  
            else:
                log.info("Data NOT written, fifo FULL!")  
    
    #print coverage report
    coverage_db.report_coverage(log.info, bins=True)
