# Copyright (c) 2016-2019, TDK Electronics
# All rights reserved.
#
# Author: Marek Cieplucha, https://github.com/mciepluc
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met 
# (The BSD 2-Clause License):
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Constrained-random verification features.

Classes:

* :class:`Randomized` - base class for randoimzed types.

"""

import random
import inspect
import itertools
import warnings

# python-constraint is an external pip-installable package used here
import constraint

class Randomized(object):
    """Base class for randomized types.

    The final class should contain defined random variables using the 
    :meth:`add_rand()` method.

    Constraints may be added and deleted using the
    :meth:`add_constraint()` and :meth:`del_constraint()` methods respectively.

    A constraint is an arbitrary function and may either return a 
    ``True``/``False`` value (*hard constraints*) or a numeric value, which may
    be interpreted as *soft constraints* or *distribution functions*.

    Constraint function arguments (names) must match final class attributes 
    (random or not). Constraints may have multiple random arguments which 
    corresponds to multi-dimensional distributions.

    The function :meth:`randomize()` performs a randomization for all random 
    variables meeting all defined constraints.

    The function :meth:`randomize_with()` performs a randomization using 
    additional constraint functions given in an argument.

    The functions :meth:`pre_randomize()` and :meth:`post_randomize()` are 
    called before and after :meth:`randomize` and should be overloaded in a 
    final class if necessary.

    If hard constraint cannot be resolved, an exception is thrown. If a soft
    constraint cannot be resolved (all acceptable solutions have zero 
    probability), then the variable value is not being randomized.

    Example:

    >>> class FinalRandomized(Randomized):
    >>>   def __init__(self, x):
    >>>       Randomized.__init__(self)
    >>>       self.x = x
    >>>       self.y = 0
    >>>       self.z = 0
    >>>
    >>>       # define y as a random variable taking values from 0 to 9
    >>>       add_rand("y", list(range(10)))
    >>>
    >>>       # define z as a random variable taking values from 0 to 4
    >>>       add_rand("z", list(range(5)))
    >>>
    >>>       # hard constraint
    >>>       add_constraint(lambda x, y: x !=y) 
    >>>       # multi-dimensional distribution
    >>>       add_constraint(lambda y, z: y + z) 
    >>>
    >>> # create randomized object instance (default values at this point)
    >>> obj_ = FinalRandomized(5)
    >>> # randomize object with additional contraint 
    >>> obj_.randomize_with(lambda z : z > 3)  

    As generating constrained random objects may involve a lot of computations,
    it is recommended to limit random variables domains and use
    :meth:`pre_randomize()`/:meth:`post_randomize()` methods where possible.
    """

    def __init__(self):
        # all random variables, map NAME -> DOMAIN
        self._randVariables = {}

        # all simple constraints: functions of single random variable and
        # optional non-random variables
        # map VARIABLE NAME -> FUNCTION
        self._simpleConstraints = {}

        # all implicit constraints: functions that requires to be resolved by a
        # Solver
        # map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implConstraints = {}

        # all implicit distributions: functions that involve implicit random
        # variables and single unconstrained variable
        # map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implDistributions = {}

        # all simple distributions: functions of unconstrained random variables
        # and non-random variables
        # map VARIABLE NAME -> FUNCTION
        self._simpleDistributions = {}

        # list of lists containing random variables solving order
        self._solve_order = []

    def add_rand(self, var, domain=None):
        """Add a random variable to the solver.

        All random variables must be defined before adding any constraint with 
        :meth:`add_constraint`. Therefore it is highly recommended to call 
        ``add_rand`` in the ``__init__`` method of your final class.

        Args:
            var (str): a variable name corresponding to the class member 
                variable.
            domain (list, optional): a list of all allowed values of the 
                variable ``var``. By default, a list with values ``0`` to 
                ``65534`` (16 bit unsigned int domain) is used.

        Examples:

        >>> add_rand("data", list(range(1024)))
        >>> add_rand("delay", ["small", "medium", "high"])
        """
        assert (not (self._simpleConstraints or
                     self._implConstraints or
                     self._implDistributions or
                     self._simpleDistributions)
                ), \
            "All random variables must be defined before adding a constraint."

        try:
            getattr(self, var)
        except:
            raise Exception("Class member '" + var + "' does not exist.")

        if not domain:
            domain = range(65535)  # 16 bit unsigned int

        self._randVariables[var] = domain  # add a variable to the map

    def add_constraint(self, cstr):
        """Add a constraint function to the solver.

        A constraint may return ``True``/``False`` or a numeric value.
        Constraint function arguments must be valid class member names (random 
        or not). Arguments must be listed in alphabetical order.

        Due to calculation complexity, it is recommended to create as few 
        constraints as possible and implement
        :meth:`pre_randomize()`/:meth:`post_randomize()` methods, or use the 
        :meth:`solve_order()` function.

        Each constraint is associated with its arguments being random 
        variables,which means for each random variable combination only one 
        constraint of the ``True``/``False`` type and one numeric may be 
        defined. The latter will overwrite the existing one.

        For example, when class has two random variables ``(x, y)``, 
        six constraint functions may be defined: boolean and numeric 
        constraints of ``x``, ``y`` and a pair ``(x, y)``.

        Args:
            cstr (func): a constraint function.

        Returns:
            func or None: an overwritten constraint or ``None`` if no 
            overwrite happened.

        Examples:

        >>> def highdelay_cstr(delay):
        >>>     return delay == "high"
        >>>
        >>> add_constraint(highdelay_cstr)  # hard constraint
        >>> add_constraint(lambda data : data < 128)  # hard constraint
        >>>
        >>> # distribution (highest probability density at the boundaries):
        >>> add_constraint(lambda data : abs(64 - data))
        >>>
        >>> # hard constraint of multiple variables (some of them may be 
        >>> # non-random):
        >>> add_constraint(lambda x,y,z : x + y + z == 0)
        >>>
        >>> # soft constraint created by applying low probability density for 
        >>> # some solutions:
        >>> add_constraint(
        >>>  lambda delay, size : 0.01 if (size < 5 & delay == "medium") else 1
        >>> )
        >>> # constraint that overwrites the previously defined one
        >>> # (data < 128)
        >>> add_constraint(lambda data : data < 256)
        """

        # just add constraint considering all random variables
        return self._add_constraint(cstr, self._randVariables)

    def solve_order(self, *orderedVars):
        """Define an order of the constraints resolving.

        Constraints are being resolved in a given order, which means that 
        randomization is called in separated steps, where at each next step
        some constraints are already resolved. Number of arguments defines 
        number of the randomization steps.
        If this funcion is specified multiple times for a given object, only
        the last one remains valid. 

        Args:
            *orderedVars (multiple str or list): Variables that are requested 
                to be resolved in an specific order.

        Example:

        >>> add_rand("x", list(range(0,10)))
        >>> add_rand("y", list(range(0,10)))
        >>> add_rand("z", list(range(0,10)))
        >>> add_rand("w", list(range(0,10)))
        >>> add_constraint(lambda x, y : x + y = 9)
        >>> add_constraint(lambda z : z < 5)
        >>> add_constraint(lambda w : w > 5)
        >>>
        >>> solve_order(["x", "z"], "y")
        >>> # In a first step, "z", "x" and "w" will be resolved, which means 
        >>> # only the second and third constraint will be applied. In a second 
        >>> # step, the first constraint will be resolved as it was requested 
        >>> # to solve "y" after "x" and "z". "x" will be interpreted as a 
        >>> # constant in this case.
        """
        self._solve_order = []
        for selRVars in orderedVars:
            if type(selRVars) is not list:
                self._solve_order.append([selRVars])
            else:
                self._solve_order.append(selRVars)

    def del_constraint(self, cstr):
        """Delete a constraint function.

        Args:
            cstr (func): a constraint function.

        Example:

        >>> del_constraint(highdelay_cstr)
        """
        self._simpleConstraints = {
          k : v for k, v in self._simpleConstraints.items() if v != cstr
        }
        self._simpleDistributions = {
          k : v for k, v in self._simpleDistributions.items() if v != cstr
        }
        self._implConstraints = {
          k : v for k, v in self._implConstraints.items() if v != cstr
        }
        self._implDistributions = {
          k : v for k, v in self._implDistributions.items() if v != cstr
        }

    def pre_randomize(self):
        """A function that is called before 
        :meth:`randomize`/:meth:`randomize_with`.

        To be overridden in a final class if used.
        """
        pass

    def post_randomize(self):
        """A function that is called after 
        :meth:`randomize`/:meth:`randomize_with`.

        To be overridden in a final class if used.
        """
        pass

    def randomize(self):
        """Randomize a final class using only predefined constraints."""
        self._randomize()

    def randomize_with(self, *constraints):
        """Randomize a final class using the additional constraints given.

        Additional constraints may override existing ones.

        Args:
            *constraints ((multiple) func): additional constraints to be 
                applied.

        """
        overwritten_constrains = []

        # add new constraints
        for cstr in constraints:
            overwritten = self.add_constraint(cstr)
            if overwritten:
                overwritten_constrains.append(overwritten)

        raise_exception = False
        try:
            self._randomize()
        except:
            raise_exception = True

        # remove new constraints
        for cstr in constraints:
            self.del_constraint(cstr)

        # add back overwritten constraints
        for cstr in overwritten_constrains:
            self.add_constraint(cstr)

        if raise_exception:
            raise Exception("Could not resolve implicit constraints!")

    def _add_constraint(self, cstr, rvars):
        """Add a constraint for a specific random variables list
        (which determines a type of a constraint - simple or implicit).
        """
        if isinstance(cstr, constraint.Constraint):
            # could be a Constraint object...
            pass
        else:
            variables = inspect.signature(cstr).parameters
            assert (list(variables) == sorted(variables)), \
                "Variables of a constraint function must be defined in \
                alphabetical order"

            # determine the function type... rather unpythonic but necessary 
            # for distinction between a constraint and a distribution
            callargs = []
            rand_variables = []
            for var in variables:
                if var in rvars:
                    rand_variables.append(var)
                    callargs.append(random.choice(rvars[var]))
                else:
                    callargs.append(getattr(self, var))

            ret = cstr(*callargs)

            def _addToMap(_key, _map):
                overwriting = None
                if _key in _map:
                    overwriting = _map[_key]
                _map[_key] = cstr
                return overwriting

            #PEP will complain, but it may be np.bool_ type!!!!
            #if type(ret) is bool:
            if ((str(ret) == "True") or (str(ret) == "False")):
                # this is a constraint
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(
                        rand_variables[0], self._simpleConstraints)
                else:
                    overwriting = _addToMap(
                        tuple(rand_variables), self._implConstraints)
            else:
                # this is a distribution
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(
                        rand_variables[0], self._simpleDistributions)
                else:
                    overwriting = _addToMap(
                        tuple(rand_variables), self._implDistributions)

            return overwriting

    def _randomize(self):
        """Call :meth:`_resolve` and 
        :meth:`pre_randomize`/:meth:`post_randomize` functions with respect to 
        defined variables resolving order.
        """

        self.pre_randomize()
        if not self._solve_order:
            #call _resolve for all random variables
            solution = self._resolve(self._randVariables)
            self._update_variables(solution)
        else:

            #list of random variables names
            remainingRVars = list(self._randVariables.keys())

            #list of resolved random variables names
            resolvedRVars = []

            #list of random variables with defined solve order
            remainingOrderedRVars = [item for sublist in self._solve_order
                                     for item in sublist]

            allConstraints = [] # list of functions (all constraints and dstr)
            allConstraints.extend([self._implConstraints[_]
                               for _ in self._implConstraints])
            allConstraints.extend([self._implDistributions[_]
                               for _ in self._implDistributions])
            allConstraints.extend([self._simpleConstraints[_]
                               for _ in self._simpleConstraints])
            allConstraints.extend([self._simpleDistributions[_]
                               for _ in self._simpleDistributions])

            for selRVars in self._solve_order:

                #step 1: determine all variables to be solved at this stage
                actualRVars = list(selRVars) #add selected
                for rvar in actualRVars:
                    remainingOrderedRVars.remove(rvar) #remove selected
                    remainingRVars.remove(rvar) #remove selected

                #if implicit constraint requires a variable which is not given
                #at this stage, it will be resolved later
                for rvar in remainingRVars:
                    rvar_unused = True
                    for c_vars in self._implConstraints:
                        if rvar in c_vars:
                            rvar_unused = False
                    for d_vars in self._implDistributions:
                        if rvar in d_vars:
                            rvar_unused = False
                    if rvar_unused and not rvar in remainingOrderedRVars:
                        actualRVars.append(rvar)
                        remainingRVars.remove(rvar)

                # a new map of random variables
                newRandVariables = {}
                for var in self._randVariables:
                    if var in actualRVars:
                        newRandVariables[var] = self._randVariables[var]

                #step 2: select only valid constraints at this stage

                #delete all constraints and add back but considering only
                #limited list of random vars
                actualCstr = []

                for f_cstr in allConstraints:
                    self.del_constraint(f_cstr)
                    f_cstr_args = inspect.signature(f_cstr).parameters
                    #add only constraints containing actualRVars but not
                    #remainingRVars
                    add_cstr = True
                    for var in f_cstr_args:
                        if (var in self._randVariables and
                            not var in resolvedRVars and
                            (not var in actualRVars or var in remainingRVars)
                            ):
                            add_cstr = False
                    if add_cstr:
                        self._add_constraint(f_cstr, newRandVariables)
                        actualCstr.append(f_cstr)

                #call _resolve for all random variables
                solution = self._resolve(newRandVariables)
                self._update_variables(solution)

                resolvedRVars.extend(actualRVars)

                #add back everything as it was before this stage
                for f_cstr in actualCstr:
                    self.del_constraint(f_cstr)

                for f_cstr in allConstraints:
                    self._add_constraint(f_cstr, self._randVariables)

        self.post_randomize()

    def _resolve(self, randomVariables):
        """Resolve constraints for given random variables."""

        # we need a copy, as we will be updating domains
        randVariables = dict(randomVariables)

        # step 1: determine search space by applying simple constraints to the
        # random variables

        for rvar in randVariables:
            domain = randVariables[rvar]
            new_domain = []
            if rvar in self._simpleConstraints:
                # a simple constraint function to be applied
                f_cstr = self._simpleConstraints[rvar]
                # check if we have non-random vars in cstr...
                # arguments of the constraint function
                f_c_args = inspect.signature(f_cstr).parameters
                for ii in domain:
                    f_cstr_callvals = []
                    for f_c_arg in f_c_args:
                        if (f_c_arg == rvar):
                            f_cstr_callvals.append(ii)
                        else:
                            f_cstr_callvals.append(getattr(self, f_c_arg))
                    # call simple constraint for each domain element
                    if f_cstr(*f_cstr_callvals):
                        new_domain.append(ii)
                # update the domain with the constrained one
                randVariables[rvar] = new_domain

        # step 2: resolve implicit constraints using external solver

        # external hard constraint solver - package python-constraint
        problem = constraint.Problem()

        constrainedVars = []  # all random variables for the solver

        for rvars in self._implConstraints:
            # add all random variables
            for rvar in rvars:
                if not rvar in constrainedVars:
                    problem.addVariable(rvar, randVariables[rvar])
                    constrainedVars.append(rvar)
            # add constraint
            problem.addConstraint(self._implConstraints[rvars], rvars)

        # solve problem
        solutions = problem.getSolutions()

        if (len(solutions) == 0) & (len(constrainedVars) > 0):
            raise Exception("Could not resolve implicit constraints!")

        # step 3: calculate implicit distributions for all random variables
        # except simple distributions

        # all variables that have defined distribution functions
        distrVars = []
        # solutions with applied distribution weights - list of maps VARIABLE
        # -> VALUE
        dsolutions = []

        # add all variables that have defined distribution functions
        for dvars in self._implDistributions:
            # add all variables that have defined distribution functions
            for dvar in dvars:
                if dvar not in distrVars:
                    distrVars.append(dvar)

        # all variables that have defined distributions but unconstrained
        ducVars = [var for var in distrVars if var not in constrainedVars]

        # list of domains of random unconstrained variables
        ducDomains = [randVariables[var] for var in ducVars]

        # Cartesian product of above
        ducSolutions = list(itertools.product(*ducDomains))

        # merge solutions: constrained ones and all possible distribution 
        # values
        for sol in solutions:
            for ducsol in ducSolutions:
                dsol = dict(sol)
                jj = 0
                for var in ducVars:
                    dsol[var] = ducsol[jj]
                    jj += 1
                dsolutions.append(dsol)

        dsolution_weights = []
        dsolutions_reduced = []

        for dsol in dsolutions:  # take each solution
            weight = 1.0
            # for all defined implicit distributions
            for dstr in self._implDistributions:
                f_idstr = self._implDistributions[dstr]
                f_id_args = inspect.signature(f_idstr).parameters
                # all variables in solution we need to calculate weight
                f_id_callvals = []
                for f_id_arg in f_id_args:  # for each variable name
                    if f_id_arg in dsol:  # if exists in solution
                        f_id_callvals.append(dsol[f_id_arg])
                    else:  # get as non-random variable
                        f_id_callvals.append(getattr(self, f_id_arg))
                # update weight of the solution - call distribution function
                weight = weight * f_idstr(*f_id_callvals)
            # do the same for simple distributions
            for dstr in self._simpleDistributions:
                # but only if variable is already in the solution
                # if it is not, it will be calculated in step 4
                if dstr in sol:
                    f_sdstr = self._simpleDistributions[dstr]
                    f_sd_args = inspect.signature(f_sdstr).parameters
                    # all variables in solution we need to calculate weight
                    f_sd_callvals = []
                    for f_sd_arg in f_sd_args:  # for each variable name
                        if f_sd_arg in dsol:  # if exists in solution
                            f_sd_callvals.append(dsol[f_sd_arg])
                        else:  # get as non-random variable
                            f_sd_callvals.append(getattr(self, f_sd_arg))
                    # update weight of the solution - call distribution 
                    # function
                    weight = weight * f_sdstr(*f_sd_callvals)
            if (weight > 0.0):
                dsolution_weights.append(weight)
                # remove solutions with weight = 0
                dsolutions_reduced.append(dsol)

        solution_choice = self._weighted_choice(
            dsolutions_reduced, dsolution_weights)
        solution = solution_choice if solution_choice is not None else {}

        # step 4: calculate simple distributions for remaining random variables
        for dvar in randVariables:
            if not dvar in solution:  # must be yet unresolved variable
                domain = randVariables[dvar]
                weights = []
                if dvar in self._simpleDistributions:
                    # a simple distribution to be applied
                    f_dstr = self._simpleDistributions[dvar]
                    # check if we have non-random vars in dstr...
                    f_d_args = inspect.signature(f_dstr).parameters
                    # list of lists of values for function call
                    f_d_callvals = []
                    for i in domain:
                        f_d_callval = []
                        for f_d_arg in f_d_args:
                            if (f_d_arg == dvar):
                                f_d_callval.append(i)
                            else:
                                f_d_callval.append(getattr(self, f_d_arg))
                        f_d_callvals.append(f_d_callval)
                    # call distribution function for each domain element to get
                    # the weight
                    weights = [f_dstr(*f_d_callvals_i)
                               for f_d_callvals_i in f_d_callvals]
                    new_solution = self._weighted_choice(domain, weights)
                    if new_solution is not None:
                        # append chosen value to the solution
                        solution[dvar] = new_solution
                else:
                    # random variable has no defined distribution function -
                    # call simple random.choice
                    if (len(domain) == 0):
                        raise Exception("Could not resolve constraints!")
                    solution[dvar] = random.choice(domain)
        return solution

    def _weighted_choice(self, solutions, weights):
        """Get a solution from the list with defined weights."""
        result = None
        non_zero_weights = [x for x in weights if x > 0]
        if non_zero_weights:
            try:
                if len(solutions) != 0:
                    import numpy
                    # pick weighted random
                    weights_norm = [_/sum(weights) for _ in weights]
                    result = numpy.random.choice(solutions, p=weights_norm)
            except ImportError:
                # if numpy not available
                min_weight = min(non_zero_weights)
                weighted_solutions = []

                for x in range(len(solutions)):
                    # insert each solution to the list multiple times
                    weighted_solutions.extend(
                        [solutions[x] for _ in range(
                            int(weights[x] * (1.0 / min_weight)))
                         ])
                result = random.choice(weighted_solutions)
        return result

    def _update_variables(self, solution):
        """Update members of the final class after randomization."""
        # update class members
        for var in self._randVariables:
            if var in solution:
                setattr(self, var, solution[var])

    #deprecated
    def addRand(self, var, domain=None):
        """.. deprecated:: 1.0"""
        warnings.warn(
         "Function addRand() is deprecated, use add_rand() instead"
        )
        self.add_rand(var, domain)

    def solveOrder(self, *orderedVars):
        """.. deprecated:: 1.0"""
        warnings.warn(
         "Function solveOrder() is deprecated, use solve_order() instead"
        )
        self.solve_order(*orderedVars)

    def addConstraint(self, cstr):
        """.. deprecated:: 1.0"""
        warnings.warn(
         "Function addConstraint() is deprecated, use add_constraint() instead"
        )
        self.add_constraint(cstr)

    def delConstraint(self, cstr):
        """.. deprecated:: 1.0"""
        warnings.warn(
         "Function delConstraint() is deprecated, use del_constraint() instead"
        )
        self.del_constraint(cstr)


