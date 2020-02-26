#########
Tutorials
#########

Functional Coverage
===================

Translating SystemVerilog Constructs to cocotb-coverage
-------------------------------------------------------



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

    covered = []

    class CdtgRandomized(crv.Randomized):

        def __init__(self):
            crv.Randomized.__init__(self)
            self.x = 0
            self.add_rand("x", list(range(10)))
            self.add_constraint(lambda x : x not in covered)

    @coverage.CoverPoint("top.cdtg_coverage", xf = lambda obj : obj.x, bins = list(range(10))) 
    def sample_coverage(obj):
        covered.append(obj.x)

    obj = CdtgRandomized()
    for _ in range(10):
        obj.randomize()
        sample_coverage(obj)




