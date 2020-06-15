#########
Tutorials
#########

Let's Start
===========

These tutorials present typical use cases of the functional coverage and constrained random verification features.
There are prepared in particular for SystemVerilog users that would like to use cocotb-coverage.
It is required that user at this level:

- has basic knowledge of Python (including collections and *lambda* expressions that are going to be used quite frequently),
- understands main cocotb concepts (coroutines, forks, yielding events),
- has basic knowledge of SystemVerilog (or any other HVL) coverage and randomization constructs.

Functional Coverage
===================

Translating SystemVerilog Constructs to cocotb-coverage
-------------------------------------------------------

In SystemVerilog *covergroups*, *coverpoints* and *cross* are unique language constructs.
There is no a straightforward equivalence between these constructs and cocotb-coverage objects.
However, a `CoverItem` is a coverage objects container, so roughly corresponds to a *covergroup*.
`CoverPoint` and `CoverCross` correspond to SV *coverpoint* and *cross*.

Sampling
~~~~~~~~

Sampling coverage in SystemVerilog is defined for each *covergroup* as a logical event (e.g. positive edge of the sampling signal). 
Alternatively, SV *covergroup* may be implicitly sampled using the built-in *sample()* method. 

.. code-block:: systemverilog

    // covergroup definition
    covergroup cg1 @ (posedge en); // sampling at rising edge of en
        ...
    endgroup
    
    // covergroup instance
    cg1 cg1_inst;

    ...
    cg1_inst.sample(); // implicit sampling of the cg1 instance cg1_inst

In cocotb-coverage, sampling is done each time when a function containing a coverage is called. 
In order to provide exactly the same functionality, a cocotb coroutine must be created that monitors the sampling signal.
Please note, that this approach may not be effective, as it makes more sense to sample a "test" event rather than "logical" event. 

In cocotb-coverage, the sampling function signature must contains the objects that are being covered.

.. code-block:: python

    @CG1
    def sampling_function(...):
        # call this function to sample the CG1 coverage

    ...
    sampling_function(...) # implicit sampling can be anywhere in the code

    ...
    @cocotb.coroutine
    def edge_sensitive_sampling():
        # process to observe the logical event that samples the coverage
        while True:
            yield RisingEdge(en)
            sampling_function(...) # implicit sampling

    cocotb.fork(edge_sensitive_sampling) # fork the process observing the sampling event


Coverage Section
~~~~~~~~~~~~~~~~

`Coverage Section <coverage_section>` is a concept introduced in cocotb-coverage, that allows for separating the coverage code from the testbench code.
It allows for packing the coverage primitives in separated blocks of code. 
Below code examples are equivalent.

.. list-table::

   * - .. code-block:: python
          :caption: sections not used

          @CoverPoint(
            "top.cg1.rw", 
             vname="rw", bins = [True, False]
          )
          @CoverPoint(
            "top.cg1.data", 
            vname="rw", bins = list(range(256))
          )
          def sampling_function():
              ...

     - .. code-block:: python
          :caption: sections used

          MyCoverage = coverage_section (
              CoverPoint(
                "top.cg1.rw", 
                vname="rw", bins = [True, False]
              ),
              CoverPoint(
                "top.cg1.data", 
                vname="rw", bins = list(range(256))
              )
          )

          ...

          @MyCoverage
          def sampling_function():
              ...  

Cover Group
~~~~~~~~~~~

In cocotb-coverage Cover Groups are created implicitly. 
The structure of the implemented coverage depends on names of explicit coverage primitives, such as `CoverPoint`.
Each explicit coverage primitive defines its position in the coverage tree using a dot-divided string. 
For example, creation of the `CoverPoint` named "a.b.c" creates a Cover Group (`CoverItem`) "a", containing a Cover Group (`CoverItem`) "b", containing a `CoverPoint` "c".

It is recommended to have a single top node of the coverage database (structure "top.*..."), however it is not mandatory. 

Cover Point
~~~~~~~~~~~

Let's take a simple example from `ASIC WORLD Functional Coverage Tutorial - part 1 <http://www.asic-world.com/systemverilog/coverage1.html>`_.

.. code-block:: systemverilog

    covergroup memory;
      address : coverpoint addr {
        bins low    = {0,50};
        bins med    = {51,150};
        bins high   = {151,255};
      }
      parity : coverpoint  par {
        bins even  = {0};
        bins odd   = {1};
      }
      read_write : coverpoint rw {
        bins  read  = {0};
        bins  write = {1};
      }
    endgroup

To create equivalent `Cover Points <CoverPoint>`, the following must be assured:

- sampling function signature must contain variables "addr", "par" and "rw",
- each `CoverPoint` must associate the "vname" field with one of that variable,
- for `CoverPoint` "memory.address", there must be an auxiliary function used that defines range bins matching used as a relation function,
- the "bins_labels" field should be used in order to bind the bins with a meaningful label. 

.. code-block:: python

    # auxiliary relation function to define bins matching within a range
    range_relation = lambda val_, bin_ : bin_[0] <= val_ <= bin_[1]

    CoverPoint(
      "memory.address", 
      vname="addr", 
      rel = range_relation,
      bins = [(0,50), (51,150), (151,255)], 
      bins_labels = ["low", "med", "high"]
    )
    CoverPoint(
      "memory.parity", 
      vname="par", 
      bins = [0, 1], bins_labels = ["even", "odd"]
    )
    CoverPoint(
      "memory.rw", 
      vname="rw", 
      bins = [0, 1], bins_labels = ["read", "write"]
    )

    # function sampling coverage must use all covered variables
    ...
    def sample_coverage(addr, par, rw):
        ...

Let's take another example of coverage - the `transition bins <http://www.asic-world.com/systemverilog/coverage9.html>`_.

.. code-block:: systemverilog

    covergroup address_cov () @ (posedge ce);
      ADDRESS : coverpoint addr {
        // simple transition bin
        bins adr_0_to_1          = (0=>1);
        bins adr_1_to_0          = (1=>0);
        bins adr_1_to_2          = (1=>2);
        bins adr_2_to_1          = (2=>1);
        bins adr_0_1_2_3         = (0=>1=>2=>3);
        bins adr_1_4_7           = (1=>4=>7);
      }
    endgroup

The same can be done in cocotb-coverage as matching the data type that contains multiple values. 
These values would represent the transition.
We need to use an auxiliary relation function and data set to store these previous values.
`Deque <https://docs.python.org/3/library/collections.html#collections.deque>`_ of fixed size can be used here. 

.. code-block:: python
  
    # auxiliary data set containing previously sampled values
    addr_prev = collections.deque(4*[0], 4) # we would need up to 4 values in this example

    # auxiliary relation function to define bins matching
    def transition_relation(val_, bin_):
       addr_prev.appendleft(val_) #we update the data set here (side effect)
       return list(addr_prev)[:len(bin_)] == bin_ #check equivalence of the meaningful elements

    CoverPoint(
      "addres_cov.ADDRESS", 
      vname="addr", 
      rel = transition_relation,
      bins = [[0, 1], [1, 0], [1, 2], [2, 1], [0, 1, 2, 3], [1, 4, 7]], 
      bins_labels = ["adr_0_to_1", "adr_1_to_0", "adr_1_to_2", "adr_2_to_1", "adr_0_1_2_3", "adr_1_4_7"]
    )

Different type of transitions (consecutive, range etc.) can be easily implemented using the approach similar to the above. 

Please note, that in cocotb-coverage all bins must be explicitly defined in the "bins" list. 
There is no option to use a wildcard or ignore bins. 
However, manipulating data sets in Python is easy, so creating a complex list is not an issue. 
Please note that "bins" must always be a list type (cannot be range or stream - must be converted).  
Few examples:

.. code-block:: python
  
    # integers 1 ... 5
    bins1 = [1, 2, 3, 4, 5] 
    # tuples (1, 1) ... (2, 2)
    bins2 = [(1, 1), (1, 2), (2, 1), (2, 2)] 
    # integers 0 ... 99
    bins3 = list(range(100)) 
    # tuples (0, 0) ... (9, 9)
    bins4 = [(x, y) for x in range (10) for y in range (10)]
    # strings
    bins5 = ["a", "b", "c"]
    # integers 0 ... 99 except divisible by 5
    bins6 = list(filter(lambda x : (x % 5) != 0, range(100)))
 

Cover Cross
~~~~~~~~~~~

Let's take another example from `ASIC WORLD Functional Coverage Tutorial - part 20 <http://www.asic-world.com/systemverilog/coverage20.html>`_.

.. code-block:: systemverilog

    covergroup address_cov ();
      ADDRESS : coverpoint addr {
        bins addr0 = {0};
        bins addr1 = {1};
      }
      CMD : coverpoint cmd {
        bins READ = {0};
        bins WRITE = {1};
        bins IDLE  = {2};
      }
      CRS_USER_ADDR_CMD : cross ADDRESS, CMD {
        bins USER_ADDR0_READ = binsof(CMD) intersect {0};
      }
      CRS_AUTO_ADDR_CMD : cross ADDRESS, CMD {
        ignore_bins AUTO_ADDR_READ = binsof(CMD) intersect {0};
        ignore_bins AUTO_ADDR_WRITE = binsof(CMD) intersect {1} && binsof(ADDRESS) intersect{0};
      }

Creating a `CoverCross` in cocotb-coverage works the same way. 
List of `CoverPoints <CoverPoint>` must be provided and cross-bins are created automatically.
Automatically created bins are tuples with number of elements equal to number of `CoverPoints <CoverPoint>`.
Basically, list of cross-bins is a Cartesian product of `CoverPoints <CoverPoint>` bins.

The list of cross-bins will have the following structure:

.. code-block:: python

    [
       (cp0_bin0, cp1_bin0, ...), (cp0_bin1, cp1_bin0, ...), ..., 
       (cp0_bin0, cp1_bin1, ...), (cp0_bin1, cp1_bin1, ...), ...,
       ...
    ]

It is possible to create a list of *ignore_bins*. 
This list should contain explicit tuples of cross-bins that should be ignored.
Additionally, if an ignore cross-bin contains a *None* value, all cross-bins with values equal to not-*None* elements of this ignore bin will be ignored.

Below is the code corresponding to the above SystemVerilog example:

.. code-block:: python
  
    CoverPoint(
      "address_cov.ADDRESS", 
      vname="addr", 
      bins = [0, 1], 
      bins_labels = ["addr0", "addr1"]
    )
    CoverPoint(
      "address_cov.CMD", 
      vname="cmd", 
      bins = [0, 1, 2], 
      bins_labels = ["READ", "WRITE", "IDLE"]
    )
    CoverCross(
      "address_cov.CRS_USER_ADDR_CMD", 
      items = ["address_cov.ADDRESS", "address_cov.CMD"],
      # default created cross-bins will be:
      # ("addr0", "READ"), ("addr0", "WRITE"), ("addr0", "IDLE"),
      # ("addr1", "READ"), ("addr1", "WRITE"), ("addr1", "IDLE")
      ign_bins = [("addr0", "WRITE"), ("addr0", "IDLE"), ("addr1", "WRITE"), ("addr1", "IDLE")]
      # OR alternatively with None value
      # ign_bins = [(None, "WRITE"), (None, "IDLE")]      
    )
    CoverCross(
      "address_cov.CRS_AUTO_ADDR_CMD", 
      items = ["address_cov.ADDRESS", "address_cov.CMD"],
      # default created cross-bins will be:
      # ("addr0", "READ"), ("addr0", "WRITE"), ("addr0", "IDLE"),
      # ("addr1", "READ"), ("addr1", "WRITE"), ("addr1", "IDLE")
      ign_bins = [("addr0", "READ"), ("addr1", "READ"), ("addr0", "WRITE")]
      # OR alternatively with None value
      # ign_bins = [(None, "READ"), ("addr0", "WRITE")]      
    )

Accessing Coverage Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each coverage primitive is a full-featured object of type `CoverItem`. 
Each of these objects can be accessed from a singleton coverage database object: `CoverageDB` organized in a dictionary data structure.
The key for each element is its full name. 
Accessing the coverage primitives allows for obtaining its properties and defining callbacks (note some of them apply only for specific types).
Few examples below:

.. code-block:: python
  
    cg_memory = coverage_db["memory"] # make a handle to the "memory" covergroup
    print(cg_memory.cover_percentage) # print the coverage level of the whole covergroup

    # create a callback for the covergroup - print info when 50% level exceeded
    cg_memory.add_threshold_callback(lambda : print("exceeded 50% coverage"), 50)

    cp_memory_addr = coverage_db["memory.address"] # make a handle to the "memory.address" coverpoint
    print(cp_memory_addr.detailed_coverage) # print the detailed coverage  

    # create a bins callback for the coverpoint - print info when "low" address bin hit
    cg_memory.add_bins_callback(lambda : print("low address bin hit"), "low")


Using CoverCheck as Assertions
------------------------------

A `CoverCheck` is a coverage type that can be used as an assertion. 
It is required to define two function for this type: a pass condition function and a fail condition function.

Basically, pass condition function must be satisfied in order to cover this coverage primitive (set coverage to 100%).
Fail condition function must NOT be satisfied in any case. 
If fail condition function is satisfied, coverage level is set to '0' permanently.
Additionally, a callback can be connected to the `CoverCheck`, to define immediate test action to be taken (such as test termination). 

It is very easy to use CoverCheck as a replacement for immediate assertion (assertions that can be evaluated instantly). 
An example can be:

.. code-block:: systemverilog

    assert a != b else $error("assertion error");

In the Python code, it is required to define a bins callback for bin "FAIL" if an error action is to be taken.

.. code-block:: python
  
    CoverCheck(
      "assertion.immediate.example", 
      f_fail = lambda a, b : a == b, # if a==b, check failed
      f_pass = lambda a, b : a == 1  # if a==1, coverage condition satisfied
    )

    coverage_db["assertion.immediate.example"].add_bins_callback(
      lambda : raise TestFailure("assertion error"),
      "FAIL"
    )
    
Writing concurrent assertions (conditions that involve logical sequences) is a bit more difficult.
First of all, the `CoverCheck` condition is evaluated only once, at the sampling event. 
To make it useful, it is required to use the same trick as for sequences coverage, i.e. store the previous values of used variables.
Not all concurrent assertions can be translated this way, but for some of them it is possible. 
Of course, sampling event can be delayed as well, which makes things a bit easier.

Let's implement an example of sequence that checks if after 'x' is set, 'y' must be set within 5 cycles.

.. code-block:: systemverilog

    assert x |-> ##[1:5] y else $error("assertion error");

To do that, we need to create a coroutine that monitors 'x' assertion and stores 'y' values for next 5 cycles.
After that time, the `CoverCheck` can be evaluated.

.. code-block:: python

    @CoverCheck(
      "assertion.concurrent.example", 
      f_fail = lambda y_prev : not 1 in y_prev,
      f_pass = lambda : True  # always return true
    )
    def sample(y_prev):
        pass

    def wait_x():
        while True:
            yield RisingEdge(dut.clk)
            if (dut.x): # wait for x set
                for ii in range(5): # store value of y for next 5 cycles
                    yield RisingEdge(dut.clk)
                    y_prev[ii] = dut.y.value
                sample(y_prev)
        
        
    coverage_db["assertion.concurrent.example"].add_bins_callback(
      lambda : raise TestFailure("assertion error"),
      "FAIL"
    )

Advanced Coverage
-----------------

In this section, a few more advanced coverage constructs are presented.
Some of them work similar way in SystemVerilog.

Weight and Coverage Level (Percentage)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All coverage primitives are associated with the following metrics:

- size (number of bins contained),
- coverage (number of bins covered),
- coverage level (coverage divided by size, in percent).

When the `CoverItem` contains multiple children, its metrics are a sum of the metrics of all of them. 
Consequently, the top `CoverItem` will contain all defined primitives, and its metrics will represent the top-level coverage.
To make some nodes more important than the others, weights can be used. 

Weight is an integer that increases the size of the `CoverItem`. 
For example, by default a `CoverPoint` containing 3 bins will have size of 3.
When assigning a weight of 2, its size will be equal to 6.
Of course, it will also increase sizes of all containers containing this `CoverPoint` and consequently will increase its impact on coverage level.

Please note that coverage primitives are not balanced. 
It means that for overall coverage percentage, the biggest contributor will be the element containing the highest number of bins. 

Below example shows two `CoverPoints <CoverPoint>` balanced to contribute exactly 50% each.

.. code-block:: python
  
    CoverPoint(
      "address.lsb", 
      vname="lsb", 
      bins = list(range(10))
    )
    CoverPoint(
      "address.msb", 
      vname="msb", 
      bins = list(range(5)), 
      weight = 2 # double the weight to match sizes of both coverpoints
    )
    
    ...
    
    n = coverage_db["address.lsb"].size              # n = 10    
    n = coverage_db["address.msb"].size              # n = 10
    n = coverage_db["address"].size                  # n = 20
    
    # assume we covered all bins from LSB, and only one bin from MSB
    
    n = coverage_db["address.lsb"].coverage          # n = 10 
    n = coverage_db["address.msb"].coverage          # n = 2
    n = coverage_db["address"].coverage              # n = 12
    p = coverage_db["address.lsb"].cover_percentage  # p = 100 
    p = coverage_db["address.msb"].cover_percentage  # p = 20
    p = coverage_db["address"].cover_percentage      # p = 60   
    

Attribute "At Least"
~~~~~~~~~~~~~~~~~~~~
    
The "at least" attribute is used to define how many times a particular bin must be hit to be considered covered.
Note that a `CoverCross` will work independently from its `CoverPoints <CoverPoint>`.
E.g. if "at least" attribute (>1) is defined for `CoverPoints <CoverPoint>` only, `CoverCross` coverage may be increasing while `CoverPoints <CoverPoint>` coverage is still 0.

A simple example below shows usage of "at least" attribute.

.. code-block:: python
  
    CoverPoint(
      "address.lsb", 
      vname="lsb", 
      bins = list(range(10)), 
      at_least = 2
    )
    CoverPoint(
      "address.msb", 
      vname="msb", 
      bins = list(range(5)), 
      at_least = 5
    )
    CoverCross(
      "address.cross", 
      items = ["address.lsb", "address.msb"]    
    )    
    
    ...
    
    # assume we sampled only once
    
    n = coverage_db["address.lsb"].coverage          # n = 0 
    n = coverage_db["address.msb"].coverage          # n = 0
    n = coverage_db["address.cross"].coverage        # n = 1    
    
Attribute "Injection"
~~~~~~~~~~~~~~~~~~~~~

The "injection" attribute is used to describe if more that one bin can be hit at once. 
By default it is set "True", meaning only one bin (first one that matches) can be hit at single sampling event.
Setting this attribute to "false" allows for matching multiple bins. 

Below example shows the difference in behavior between similar `CoverPoints <CoverPoint>`.

.. code-block:: python

    def is_divider(number, divider):
        return number % divider == 0
  
    CoverPoint(
      "cp.injective", 
      rel = is_divider,
      bins = [1, 2, 3] 
    )
    CoverPoint(
      "cp.non-injective",
      rel = is_divider,
      bins = [1, 2, 3],
      inj = False
    )

    # assume we sampled "9" once
    n = coverage_db["cp.injective"].coverage          # n = 1, only "1" sampled
    n = coverage_db["cp.non-injective"].coverage      # n = 2, "1" and "3" sampled


Constrained Random Verification
===============================

Translating SystemVerilog Constructs to cocotb-coverage
-------------------------------------------------------

In SystemVerilog constrained randomization is managed by "randomizing" defined objects. 
Such object definition contains random variables (denoted by *rand* modifiers) and constraints, which are function-like language constructs with specific internal syntax.
Random objects are used in the testbench like any regular objects, and user can call the built-in *randomize* method in order to perform actual randomization. 

The cocotb-coverage constrained randomization mechanism works very similarly. 
The implemented randomized class should:

- inherit the base class `Randomized`,
- define random variables using `add_rand` method,
- define constraints (optionally).

Constraints are arbitrary functions of random (and possibly non-random) class members that return "True"/"False" value. 

Let's take an example from `ASIC WORLD Random Constraints Tutorial - part 6 <http://http://www.asic-world.com/systemverilog/random_constraint6.html>`_.

.. code-block:: systemverilog

    class frame_t;
      rand bit [7:0] src_port;
      rand bit [7:0] des_port;
      constraint c {
         // inclusive
         src_port inside { [8'h0:8'hA],8'h14,8'h18 };
         // exclusive
          ! (des_port inside { [8'h4:8'hFF] });
      }
      function void post_randomize();
        begin
          $display("src port : %0x",src_port);
          $display("des port : %0x",des_port);
        end
      endfunction
    endclass


The following functionality is implemented:

- there are two random variables: "src_port" and "des_port",
- "src_port" is 8-bit and takes values from '0x00' to '0x0A', '0x14' or '0x18',
- "des_port" is 8-bit and takes all possible values except '0x04' to '0xFF', 
- after randomization, values are displayed.

Implementing the same functionality in cocotb-coverage is pretty straightforward.

.. code-block:: python

    class frame_t(crv.Randomized):                      # inherit crv.Randomized
        
        def __init__(self):
            crv.Randomized.__init__(self)               # initialize super-class
            self.src_port = 0                           # define class members and their default values
            self.des_port = 0
            self.add_rand("src_port", list(range(256))) # full 8-bit space
            self.add_rand("des_port", list(range(256))) # full 8-bit space

            # define constraints (divide into two constraints compared to SV example)
            def c_1(src_port):
                return src_port in (list(range(0x0A + 1)) + [14, 20])
                
            def c_2(des_port):
                return not des_port in list(range(0x04, 0xFF + 1))
            
            # add constraints
            self.add_constraint(c_1)
            self.add_constraint(c_2)
            
        def post_randomize(self):
            print("src port : %0x", self.src_port)
            print("des port : %0x", self.des_port)


Please note, that in this particular example there is no need to define constraints, as domains can be defined straightway:

.. code-block:: python

      self.add_rand("src_port", list(range(0x0A + 1)) + [14, 20]) 
      self.add_rand("des_port", list(range(0x04)))
      
More complex functions can be also used as constraints, similar way as more complex constructs in SystemVerilog.
An example of conditional constraint is presented below. 

.. code-block:: systemverilog

    constraint cstr_frame_sizes {
      if (size == RUNT)  {
        length >= 0;
        length <= 63;
      } else if (size == OVERSIZE) {
        length >= 1501;
        length <= 5000;
      }
    }
        
.. code-block:: python

    def cstr_frame_sizes(length, size):
        if (size == "RUNT"):
            return 0 <= length <= 63
        else if (size == "OVERSIZE"):
            return 1501 <= length <= 5000

Constraints Properties
~~~~~~~~~~~~~~~~~~~~~~

As already said, in cocotb-coverage constraints are simple functions that return "True"/"False" value.
They are hard constraints, which means that in case they cannot be resolved, an exception is risen.
It is possible to define constraints that return numerical value.
They are called distributions and described in a separate section.

Constraints, being functions, are also regular objects, which means they can be manipulated the same way as other Python components.
Constraints can also be defined using *lambda* expressions.

Each implemented constraint must literally contain random variables (that are under constrain) in the signature.
Additional important property is that constraints can be defined only once for a given variable or set of variables.
If multiple constraints are defined, the later overrides the existing one. 
The variables order in the constraint signature must be alphabetical.

Let's take an example of the object which contains 3 variables: "x", "y" and "z", where "x" and "y" are randomized.
It means, we can define the following constraints: only for "x", only for "y" and for "x" combined with "y".
Not-randomized class members ("z") can be used in the constraints as well.

.. code-block:: python

    class RandExample(crv.Randomized):
        
        def __init__(self, z):
            crv.Randomized.__init__(self)                   # initialize super-class
            self.x = 0                                      # define class members and their default values
            self.y = 0
            self.z = z                                      # "z" is not a random variable
            
            self.x_c = lambda x, z: x > z                   # define a constraint that is not used by default
            
            self.add_rand("x", list(range(16)))             # full 4-bit space
            self.add_rand("y", list(range(16)))             # full 4-bit space
            
            # add constraints
            self.add_constraint(lambda x, z : x != z)       # constraint for standalone "x"
            self.add_constraint(lambda y, z : y <= z)       # constraint for standalone "y"
            self.add_constraint(lambda x, y : x + y == 8)   # constraint for combined "x" and "y"          
            
        # example simple randomization
        foo = RandExample(5)
        foo.randomize()

        # example randomization with overridden constraint
        bar = RandExample(6)
        bar.randomize_with(bar.x_c)                         # this constraint overrides existing one "x != z"
    

Class `Randomized`
~~~~~~~~~~~~~~~~~~

Class `Randomized` is used as a base class for all components that are implementing presented constrained randomization functions.
This class provides the following methods:

- `add_rand` - adds a random variable and specifies its domain (space),
- `add_constraint` - adds a constraint function to the solver,
- `del_constraint` - removes a constraint function from the solver,
- `solve_order` - optionally specifies the order of randomizing variables,
- `pre_randomize` - function automatically called before `randomize`/`randomize_with`,
- `post_randomize` - function automatically called after `randomize`/`randomize_with`,
- `randomize` - main function that picks random values of the variables satisfying given constraints,
- `randomize_with` - similar to `randomize()`, but satisfies additional given constraints.

The latter four are equivalent to their SystemVerilog correspondents.
The `solve_order` method roughly corresponds to the SystemVerilog *solve ... before* construct.
In the `solve_order` method user may define an order of assigning random values to variables, which also determines the order of resolving constraints.
Note, that because of this, it may happen that in some cases constraints cannot be resolved.

Let's try to apply a `solve_order` for the example presented above.
We can try to resolve "x" before "y" or the opposite.
If we resolve "x" before "y", in the first step only constraint "x != z" is to be met. 
So it may happen that if e.g. "x = 10" is picked, in the next step constraint "x + y == 8" cannot be satisfied under any condition.
If we resolve "y" before "x", in the first step only constraint "y <= z" will be applied. 
So, in case that "z > 8" next step constraints again may be not met.
`solve_order` method is discussed more in the "performance" section.
  

Distributions
-------------

TODO



Randomization Order and Performance Issues
------------------------------------------

From the computational complexity perspective, it is important to realize that constraint solver performance greatly depends on the search space. 
The complexity increases with the search space size, so it is recommended to plan the constrained randomization strategy that allows for reduction of this problem. 
Search space size is related to the domain sizes of the random variables that are constrained together. 

There are few solutions that can be implemented in order to reduce the constraint solver problem complexity:

- Reducing domain sizes of random variables
- Limiting number of constraints defined
- Splitting the randomization routine into subroutines (using `solve_order` function)
- Using random generation features out of the cocotb-coverage (`pre_randomize` and `post_randomize` functions can be used)

Recommended strategy for large-domain variables can be to use constraint solver to determine the data ranges, and then use `post_randomize` to pick the actual random data.
An example is provided below.

.. code-block:: python

    # not good - large domains

    self.add_rand("addr", list(range(2**16)))
    self.add_rand("packet_size", list(range(1000)))
  
    # better - variables with limited ranges
    
    # MSBs randomized using constraint solver, LSBs assumed fully random
    self.add_rand("addr_msb", list(range(2**8)))
    
    # auxiliary random variable with packet size ranges
    self.add_rand("packet_size_range", ["min", "small", "med", "large", "max"])   
  
    # final randomization of the variables "addr" and "packet_size" is done below
    def post_randomize(self):
        
        addr_lsb = np.random.randint(2**8)
        self.addr = self.addr_msb << 8 + addr_lsb
        
        self.packet_size = \
            1                           if self.packet_size_range == "min" else
            np.random.randint(2,16)     if self.packet_size_range == "small" else
            np.random.randint(16,256)   if self.packet_size_range == "med" else
            np.random.randint(256,1000) if self.packet_size_range == "large" else
            1000                      # if self.packet_size_range == "max"


Note, that constraint solver engine is in operation only for hard constraints that involve multiple variables.
Only this case can cause a computational complexity expansion.
So the example above, assuming that variables "addr" and "packet_size" are not involved in any complex constraints, may not require simplification at all.

Example of variables constrained together is shown below.
The search space size is 128x128x128, so big enough to possibly cause a performance drop.
But, when analyzing the constraints it becomes clear that they can be satisfied for any value of "x".
Because of that, the problem can be split into subroutines: randomization of "x" and randomization of "y" and "z".
That reduces the search space to 128 + 128x128.

.. code-block:: python

    self.add_rand("x", list(range(128)))
    self.add_rand("y", list(range(128)))
    self.add_rand("z", list(range(128)))

    self.add_constraint(lambda x, y: x < 2*y)
    self.add_constraint(lambda y, z: y + z == 128)
    self.add_constraint(lambda x, z: (x+z)%2 == 0)  

    # randomize "x" first, then "y" and "z"
    self.solve_order('x', ['y', 'z'])  
    
Note that in this particular example, the different randomization order ("y" and "z" before "x") cannot be used, because in case that "y"=0 is picked, first constraint cannot be met.

The same rules as above are valid for distributions. 

The last comment is about the operations order when calling a `randomize` routine. 
We can divide defined constraints into the following groups, which is also consistent with the problem resolving steps:

a) hard constraints of single variables,
b) hard constraints of multiple variables,
c) distributions of multiple variables, 
d) distributions of single variables. 

Step (a) is not a computationally complex task and is always resolved prior to any complex hard constraint (that may or may not involve the same variables).
Step (b) is a routine that requires external solver - it is time consuming and it is suggested to simplify this step using the techniques discussed above.
Step (c) is a distribution calculation - note at this stage the search space is reduced because of hard constraints already applied (some solutions are already rejected). 
If search space is still big at this point, it may be also required to simplify it. 
On the other hand, it is difficult to imagine a practical example of creating a multi-dimensional distribution of more than 2 variables. 
Step (d) is a single-dimensional distribution calculation, which is not expected to be computationally complex.

Coverage-Driven Test Generation 
================================

The following example shows how to implement a coverage-driven test generation idea.
The goal is to use coverage metrics in a run time in order to dynamically adjust randomization. 
As an outcome, the simulation time can be greatly reduced, because already covered data is excluded from the randomization set.

An example code is presented below. 
It is required to create a set (e.g. list) containing already covered data (*covered*). 
The constraint function must be created such way, that already covered data is excluded from randomization (randomized data not present in *covered* set).
When sampling the coverage, the newly covered value should be added to the set (this is done in function *sample_coverage()*).

Each time the `randomize` function is called after sampling coverage with the randomization constraints active, already covered data will not be picked again. 
In the given example, 10 randomizations are required to fully cover the *CdtgRandomized.x* variable space.

.. code-block:: python

    covered = [] #list to store already covered data

    class CdtgRandomized(crv.Randomized):

        def __init__(self):
            crv.Randomized.__init__(self)
            self.x = 0
            self.add_rand("x", list(range(10)))
            self.add_constraint(lambda x : x not in covered) # do not pick items from the list

    @coverage.CoverPoint("top.cdtg_coverage", xf = lambda obj : obj.x, bins = list(range(10))) 
    def sample_coverage(obj):
        covered.append(obj.x) # extend the list with sampled value

    obj = CdtgRandomized()
    for _ in range(10):
        obj.randomize()
        sample_coverage(obj)

