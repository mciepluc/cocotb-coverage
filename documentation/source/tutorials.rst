#########
Tutorials
#########

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

    //covergroup definition
    covergroup cg1 @ (posedge en); //sampling at rising edge of en
        ...
    endgroup
    
    //covergroup instance
    cg1 cg1_inst;

    ...
    cg1_inst.sample(); //implicit sampling of the cg1 instance cg1_inst

In cocotb-coverage, sampling is done each time when a function containing a coverage is called. 
In order to provide exactly the same functionality, a cocotb couroutine must be created that monitors the sampling signal.
Please note, that this approach may not be effective, as it makes more sense to sample a "test" event rather than "logical" event. 

In cocotb-coverage, the sampling function signature must contains the objects that are being covered.

.. code-block:: python

    @CG1
    def sampling_function(...):
        #call this function to sample the CG1 coverage

    ...
    sampling_function(...) #implicit sampling can be anywhere in the code

    ...
    @cocotb.coroutine
    def edge_sensitive_sampling():
        #process to observe the logical event that samples the coverage
        while True:
            yield RisingEdge(en)
            sampling_function(...) #implicit sampling

    cocotb.fork(edge_sensitive_sampling) #fork the process observing the sampling event


Coverage Section
~~~~~~~~~~~~~~~~

`Coverage Section <coverage_section>` is a concept instroduced in cocotb-coverage, that allows for separating the coverage code from the testbench code.
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

Let's take a simple example from `ASIC WORLD Functional Coverage Tutorial <http://www.asic-world.com/systemverilog/coverage1.html>`_.

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

- sampling funcion signature must containt variables "addr", "par" and "rw",
- each `CoverPoint` must associate the "vname" field with one of that variable,
- for `CoverPoint` "memory.address", there must be an auxiliary function used that deinfes range bins matching used as a relation function,
- the "bins_labels" field should be used in order to bind the bins with a meaningful label. 

.. code-block:: python

    #auxiliary relation function to define bins matching within a range
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

    #function sampling coverage must use all covered variables
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
  
    #auxiliary data set containing previously sampled values
    addr_prev = collections.deque(4*[0], 4) # we would need up to 4 values in this example

    #auxiliary relation function to define bins matching
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

Plese note, that in cocotb-coverage all bins must be explicitly defined in the "bins" list. 
There is no option to use a wildacrd or ignore bins. 
However, manipulating data sets in Python is easy, so creating a complex list is not an issue. 
Please note that "bins" must always be a list type.
 

Cover Cross
~~~~~~~~~~~



TODO

Using CoverCheck as Assertions
------------------------------

TODO


Advanced Coverage
-----------------

TODO


Constrained Random Verification
===============================


Translating SystemVerilog Constructs to cocotb-coverage
-------------------------------------------------------

TODO

Distributions
-------------

TODO

Advanced Constraints
--------------------

TODO

Randomization Order and Performance Issues
------------------------------------------

TODO

Coverage-Driven Test Generation 
================================

The following example shows how to implement a coverage-driven test generation idea.
The goal is to use coverage metrics in a run time in order to dynamically adjust randomization. 
As an outcome, the simulation time can be greatily recuced, because already covered data is excluded from the randomization set.

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
            self.add_constraint(lambda x : x not in covered) #do not pick items from the list

    @coverage.CoverPoint("top.cdtg_coverage", xf = lambda obj : obj.x, bins = list(range(10))) 
    def sample_coverage(obj):
        covered.append(obj.x) #extend the list with sampled value

    obj = CdtgRandomized()
    for _ in range(10):
        obj.randomize()
        sample_coverage(obj)




