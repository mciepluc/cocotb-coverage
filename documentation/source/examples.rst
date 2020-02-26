########
Examples
########

FIFO (examples/fifo)
====================

This example tests a simple FIFO block.

DUT
---

The FIFO is a 16 x 8-bit memory with a simple single 8-bit input (*data_in*) and single 8-bit output data interface (*data_out*).
There is a data read (*rd*) and write (*wr*) strobe signal.
FIFO reports its status using the following output bits:

- *fifo_full* - full indicator,
- *fifo_empty* - empty indicator,
- *fifo_threshold* - threshold indicator (25% full),
- *fifo_overflow* - fifo overflow indicator (attempt to write data when FIFO full),
- *fifo_underflow* - fifo underflow indicator (attempt to read data when FIFO empty).


Testbench
---------

The test envinroment randomly performs a read/write operation and checks the data consistency. 
The functional coverage checks if read/write operation has been executed in any possible FIFO state.

The FIFO status is represented in an instance of the class *FifoStatus*.
This object contains the method *update()*, which reads the status of the DUT.

.. code-block:: python

    class FifoStatus():

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

The main data processing routine is defined in the function *process_data()*. 
This function returns the read or written data and the status if the operation ended successfully (which depends on the FIFO satus). 
The functional coverage is sampled at this function.

.. code-block:: python

    FIFO_Coverage = coverage_section (
      CoverPoint("top.rw", vname="rw", bins = [True, False]),
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

A simple FIFO model is implemented as a double-ended queue. 
At each successfull write to the FIFO, the data is also written to the FIFO model. 
At each successfull read from the FIFO, the data concistency is checked with the FIFO model (and removed from the queue).

.. code-block:: python

    fifo_model = deque() #simple scoreboarding - FIFO model as double-ended queue

The main loop performs random operations in the following order:

- randomize the type of transaction and data,
- update the FIFO status,
- process the data to/from the FIFO,
- depending on data processing status, check data consistency or update FIFO model content.

.. code-block:: python

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

Packet Switch (examples/pkt_switch)
===================================

This example tests a simple packet switch. 
The switch routes an incoming packet to one or both of the two outgoing interfaces, depending on configuration.

DUT
---

The packet switch has a single data input interface (*datain_data*) and two data output interfaces (*dataout0_data*, *dataout1_data*). 
There are data valid strobes associated with each interface (*datain_valid*, *dataout0_valid*, *dataout1_valid*).
Depending on configuration, the packet transmitted to the input interface is passed to first, second or both otuput interfaces.

There is also a configuration interface which allows for accessing the configuration registers (write-only).
The register write operation is performed when the write strobe is high (*crtl_wr*). The *ctrl_data* is written under the *ctrl_addr* address.

There are the following configuration registers:

+------------+----------------------------------------------------+
| Address    | Function                                           |
+============+====================================================+
| 000        | settings:                                          |
|            |                                                    |
|            | - bit 0   - enable address-based filtering         |
|            | - bit 1   - enable length-based filtering          |
|            | - bit 2   - transmit packet on both interfaces     |
|            | - bit 3-7 - UNUSED                                 |
+------------+----------------------------------------------------+
| 010        | address for address-based filtering                |
+------------+----------------------------------------------------+
| 011        | address based filtering mask                       |
+------------+----------------------------------------------------+
| 100        | lower size limit for length based filtering        |
+------------+----------------------------------------------------+
| 101        | uppoer size limit for length based filtering       |
+------------+----------------------------------------------------+

If the packed is not filtered or opion to transmit packet on both interfaces is enabled, it is transmitted on interface 0. 
If the packed is filtered or opion to transmit packet on both interfaces is enabled, it is transmitted on interface 1. 

The packet structure is as follows:

+------------+----------------------------------------------------+
| Byte       | Field                                              |
+============+====================================================+
| 0          | Address (0x00- 0xFF)                               |
+------------+----------------------------------------------------+
| 1          | Length (0x03- 0x20)                                |
+------------+----------------------------------------------------+
| 2-31       | Payload                                            |
+------------+----------------------------------------------------+

The packet bytes are transmitted starting from byte 0. 
The packed is transmitted continuously, so data valid strobe must not be deasserted in the middle of the packet.
The transition 1 -> 0 on the data valid strobe denotes the end of the packet. 

The address-based filtering is active when packet address bits marked by the mask (reg address 011) are equal to the filtering address bits (reg address 010). 
The length-based filtering is active when packet length is greater than lower size limit (reg address 100) and lower than upper size limit (reg address 101).
 
Testbench
---------

The test envinroment randomly transfers packets using different configurations and checks the data consistency. 

The packet object is represented by the *Packet* class.
Randomized are fields Address (*addr*) and Length (*len*). 
The Payload (*payload*) content is randomized using the `post_randomize` method.

.. code-block:: python

    class Packet(Randomized):
        def __init__(self, data = [0, 3, 0]):
            Randomized.__init__(self)
            self.addr = data[0]
            self.len = len(data)
            self.payload = data[2:]

            self.add_rand("addr", list(range(256)))
            self.add_rand("len", list(range(3,32)))

        def post_randomize(self):
            self.payload = [random.randint(0,255) for _ in range(self.len-2)]


There are driver (*PacketIFDriver*) and monitor (*PacketIFMonitor*) implemented for the packet interface.
Driver (*driver*) is connected to the *datain* interface, while two monitors are connected to the *dataout0* (*monitor0*) and *dataout1* (*monitor1*) interface.

.. code-block:: python

    driver = PacketIFDriver(dut, name="datain", clock=dut.clk)
    monitor0 = PacketIFMonitor(dut, name="dataout0", clock=dut.clk)
    monitor1 = PacketIFMonitor(dut, name="dataout1", clock=dut.clk)

For scoreboarding there are queues implemented, associated with each output interface.
The monitors callbacks are used to check if received transaction has been expected (for both interfaces separately). 

.. code-block:: python

    expected_data0 = [] #queue of expeced packet at interface 0
    expected_data1 = [] #queue of expeced packet at interface 1

    def scoreboarding(pkt, queue_expected):       
        assert pkt.addr == queue_expected[0].addr
        assert pkt.len == queue_expected[0].len
        assert pkt.payload == queue_expected[0].payload
        queue_expected.pop()
        
    monitor0.add_callback(lambda _ : scoreboarding(_, expected_data0))
    monitor1.add_callback(lambda _ : scoreboarding(_, expected_data1))

The functional coverage is sampled at the logging function call. 
The following features are covered:

- length of the packet,
- type of the filtration (disabled, address filtering, lenght filtering or transmit on both interfaces),
- address filtering (bitwise AND of the address and mask),
- length filtering (lower an upper limit),
- cross of the packet length with the filtering limit.

.. code-block:: python

    @CoverPoint(
      "top.packet_length", 
      xf = lambda pkt, event, addr, mask, ll, ul: pkt.len,    #packet length
      bins = list(range(3,32))                                #may be 3 ... 32 bytes
    )
    @CoverPoint("top.event", vname="event", bins = ["DIS", "TB", "AF", "LF"])
    @CoverPoint(
      "top.filt_addr",  
      xf = lambda pkt, event, addr, mask, ll, ul: addr & mask,  #filtering based on a particular bits in header 
      bins = list(range(32))                                    #all options possible
    )
    @CoverPoint(
      "top.filt_len_eq", 
      xf = lambda pkt, event, addr, mask, ll, ul: ll == ul,  #filtering of a single packet length 
      bins = [True, False]
    )
    @CoverPoint(
      "top.filt_len_ll", 
      vname = "ll",                    #lower limit of packet length
      bins = list(range(3,31)) 
    )
    @CoverPoint(
      "top.filt_len_ul", 
      vname = "ll",                    #upper limit of packet length
      bins = list(range(3,32)) 
    )
    @CoverCross(
      "top.filt_len_ll_x_packet_length", 
      items = ["top.packet_length", "top.filt_len_ll"]
    )
    @CoverCross(
      "top.filt_len_ul_x_packet_length", 
      items = ["top.packet_length", "top.filt_len_ul"]
    )

The main loop performs random operations in the following order:

- randomize the type of transaction, data and configuration,
- configure the DUT and update the scoreboard queues,
- request the driver to send the packet,
- log the performed transaction (functional coverage is sampled here).

The scoreboarding is done concurrently to the main loop operations. 

.. code-block:: python

    for _ in range(1000): #is that enough repetitions to ensure coverage goal? Check out!

        event = random.choice(["DIS", "TB", "AF", "LF"])
        #DIS - disable filtering : expect all packets on interface 0
        #TB  - transmit bot : expect all packets on interface 0 and 1
        #AF  - address filtering : expect filtered packets on interface 1, others on 0
        #LF  - length filtering : expect filtered packets on interface 1, others on 0

        #randomize test data
        pkt = Packet();
        pkt.randomize()
        addr = random.randint(0, 0xFF)
        mask = random.randint(0, 0xFF)
        low_limit = random.randint(3,31)
        up_limit = random.randint(low_limit,32)

        #expect the packet on the particular interface
        if event is "DIS":
            yield disable_filtering()
            expected_data0.append(pkt)       
        elif event is "TB":
            yield enable_transmit_both()
            expected_data0.append(pkt)
            expected_data1.append(pkt)    
        elif event is "AF":
            yield enable_addr_filtering(addr, mask)
            if ((pkt.addr & mask) == (addr & mask)):
                expected_data1.append(pkt)
            else:
                expected_data0.append(pkt)
        elif event is "LF":
            yield enable_len_filtering(low_limit, up_limit)
            if (low_limit <= pkt.len <= up_limit):
                expected_data1.append(pkt)
            else:
                expected_data0.append(pkt)       

        #wait DUT
        yield driver.send(pkt)

        #LOG the action
        log_sequence(pkt, event, addr, mask, low_limit, up_limit)      


