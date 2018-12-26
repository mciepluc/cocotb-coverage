
'''Copyright (c) 2016-2018, TDK Electronics
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
Functional Coverage features.

Global variable:
coverage_db - a coverage prefix tree (map) containing all coverage objects with
              name string as a key

Classes:
CoverItem  - coverage base class, corresponds to a covergroup, created 
             automatically
CoverPoint - a cover point with bins
CoverCross - a cover cross with references to CoverPoints
CoverCheck - a cover point which checks only a pass/fail condition

Functions:
reportCoverage(logger, bins) - prints coverage
coverageSection(*CoverItems) - allows for convenient definition of multiple 
  coverage items and combines them into a single decorator

"""

from functools import wraps
from collections import OrderedDict
import inspect
import operator
import itertools

# global variable collecting coverage in a prefix tree (trie)
coverage_db = {}

class CoverItem(object):
    """
    Class used to describe coverage groups.
    CoverItem objects are created automatically. 
    """

    def __init__(self, name):
        self._name = name
        self._size = 0
        self._coverage = 0
        self._parent = None
        self._children = []

        self._threshold_callbacks = {}
        self._bins_callbacks = {}

        # check if parent exists
        if "." in name:
            parent_name = ".".join(name.split(".")[:-1])
            if not parent_name in coverage_db:
                CoverItem(name=parent_name)

            self._parent = coverage_db[parent_name]
            self._parent._children.append(self)

        coverage_db[name] = self

    def _update_coverage(self, coverage):
        current_coverage = self._coverage
        self._coverage += coverage
        if self._parent is not None:
            self._parent._update_coverage(coverage)

        # notify callbacks
        for ii in self._threshold_callbacks:
            if (ii > 100 * current_coverage / self.size and
                ii <= self.cover_percentage):
                self._threshold_callbacks[ii]()

    def _update_size(self, size):
        self._size += size
        if self._parent is not None:
            self._parent._update_size(size)

    def add_threshold_callback(self, callback, threshold):
        self._threshold_callbacks[threshold] = callback

    def add_bins_callback(self, callback, bins):
        self._bins_callbacks[bins] = callback

    @property
    def size(self):
        return self._size

    @property
    def coverage(self):
        return self._coverage

    @property
    def cover_percentage(self):
        return 100 * self._coverage / self._size

    @property
    def detailed_coverage(self):
        coverage = []
        for child in self._children:
            coverage.append(child.detailed_coverage)
        return coverage


class CoverPoint(CoverItem):
    """
    Class used to create coverage points as decorators. Sampling matches 
    predefined bins according to the rule rel(xf(args), bin) == True 
    Syntax:
    @coverage.CoverPoint(name, vname, xf, rel, bins, weight, at_least, inj)
    Where:
    name - a CoverPoint path and name, defining its position in a coverage trie

    vname - (optional) a name of the variable to be covered (use it only when
            covering a SINGLE variable)
    xf - (optional) transformation function, which transforms arguments of the 
         decorated function
    If vname and xf not defined, matched is a single input arguments (if only 
    one exists) or a tuple (if multiple exist).
    Note that "self" argument is ALWAYS removed from the argument list. 

    bins - a list of bins objects to be matched

    rel - (optional) relation function which defines bins matching relation (by 
          default, equality operator)
    
    weight - (optional) a CoverPoint weight (by default 1)
    at_least - (optional) defines number of hits per bin to be considered as c
               overed (by default 1)
    inj - (optional) defines if more than single bin can be matched at one 
          sampling (default False)

    Example:
    @coverage.CoverPoint( #covers (arg/2) < 1...5 (5 bins)
      name = "top.parent.coverpoint1", 
      xf = lambda x : x/2, 
      rel = lambda x, y : x < y, 
      bins = list(range(1,5))
    )
    @coverage.CoverPoint( #covers (arg) == 1...5 (5 bins)
      name = "top.parent.coverpoint2", 
      vname = "arg",
      bins = list(range(1,5))
    )
    def decorated_fun1(self, arg):
      ...

    @coverage.CoverPoint( #covers (arg1, arg2) == (1, 1) or (0, 0) (2 bins)
      name = "top.parent.coverpoint3", 
      bins = [(1,1), (0,0)]
    )
    def decorated_fun1(self, arg1, arg2):
      ...

    """

    # conditional Object creation, only if name not already registered
    def __new__(cls, name, vname = None, xf=None, rel=None, bins=[], weight=1, at_least=1, 
                inj=False):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super(CoverPoint, cls).__new__(CoverPoint)

    def __init__(self, name, vname = None, xf=None, rel=None, bins=[], weight=1, at_least=1, 
                 inj=False):
        if not name in coverage_db:
            CoverItem.__init__(self, name)
            if self._parent is None:
                raise Exception("CoverPoint must have a parent (parent.CoverPoint)")

            self._transformation = xf
            self._vname = vname

            # equality operator is the defult bins matching relation
            self._relation = rel if rel is not None else operator.eq
            self._weight = weight
            self._at_least = at_least
            self._injection = inj


            if (len(bins) != 0):
                self._size = self._weight * len(bins)
                self._hits = OrderedDict.fromkeys(bins, 0)
            else:  # if no bins specified, add one bin equal True
                self._size = self._weight
                self._hits = OrderedDict.fromkeys([True], 0)

            # determines whether decorated a bound method
            self._decorates_method = None
            # determines whether transformation function is a bound method
            self._trans_is_method = None
            self._parent._update_size(self._size)

            self._new_hits = []  # list of bins hit per single function call

    def __call__(self, f):
        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):

            # if transformation function not defined, simply return arguments
            if self._transformation is None:
                if self._vname is None:
                    def dummy_f(*cb_args):  # return a tuple or single object
                        if len(cb_args) > 1:
                            return cb_args
                        else:
                            return cb_args[0]
                else: #if vname defined, match it to the decroated function args
                    arg_names = list(inspect.signature(f).parameters)
                    idx = arg_names.index(self._vname)
                    def dummy_f(*cb_args):
                        return cb_args[idx]                        
 
                self._transformation = dummy_f

            # for the first time only check if decorates method in the class
            if self._decorates_method is None:
                self._decorates_method = False
                for x in inspect.getmembers(cb_args[0]):
                    if '__func__' in dir(x[1]):
                        # compare decorated function name with class functions
                        self._decorates_method = f.__name__ == x[1].__func__.__name__
                        if self._decorates_method:
                            break

            # for the first time only check if a transformation function is a
            # method
            if self._trans_is_method is None:
                self._trans_is_method = "self" in inspect.signature(
                    self._transformation).parameters

            current_coverage = self.coverage
            self._new_hits = []

            # if function is bound then remove "self" from the arguments list
            if self._decorates_method ^ self._trans_is_method:
                result = self._transformation(*cb_args[1:])
            else:
                result = self._transformation(*cb_args)

            # compare function result using relation function with matching
            # bins
            for bins in self._hits:
                if self._relation(result, bins):
                    self._hits[bins] += 1
                    self._new_hits.append(bins)
                    # check bins callbacks
                    if bins in self._bins_callbacks:
                        self._bins_callbacks[bins]()
                    # if injective function, continue through all bins
                    if not self._injection:
                        break

            # notify parent about new coverage level
            self._parent._update_coverage(self.coverage - current_coverage)

            # check threshold callbacks
            for ii in self._threshold_callbacks:
                if (ii > 100 * current_coverage / self.size and 
                    ii <= 100 * self.coverage / self.size):
                    self._threshold_callbacks[ii]()

            return f(*cb_args, **cb_kwargs)
        return _wrapped_function

    @property
    def coverage(self):
        coverage = self._size
        for ii in self._hits:
            if self._hits[ii] < self._at_least:
                coverage -= self._weight
        return coverage

    @property
    def detailed_coverage(self):
        return self._hits

    @property
    def new_hits(self):
        return self._new_hits


class CoverCross(CoverItem):
    """
    Class used to create coverage crosses as decorators. It matches tuples 
    cross-bins which are Cartesian products of bins defined in CoverPoints 
    (items).
    Syntax:
    @coverage.CoverCross(name, items, ign_bins, weight, at_least)
    Where:
    name - a CoverCross path and name, defining its position in a coverage trie
    items - a list of CoverPoints by names, to create a Cartesian product of 
            cross-bins
    ign_bins - (optional) a list of bins to be ignored
    weight - (optional) a CoverCross weight (by default 1)
    at_least - (optional) defines number of hits per bin to be considered as 
               covered (by default 1)

    Example:
    @coverage.CoverPoint(
      name = "top.parent.coverpoint1", 
      xf = lambda x, y: x, 
      bins = range(1,5)
    )
    @coverage.CoverPoint(
      name = "top.parent.coverpoint2", xf = 
      lambda x, y: y, 
      bins = range(1,5)
    )
    @coverage.CoverCross(
      name = "top.parent.covercross", 
      items = ["top.parent.coverpoint1", "top.parent.coverpoint2"],
      ign_bins = [(1,1), (5,5)],
    )
    def decorated_fun(self, arg_a, arg_b):
      ...
    Bin from the bins list [(1,2),(1,3)...(5,4)] will be matched when a tuple 
    (x=arg_a, y=arg_b) sampled at decorated_fun call.
    """

    # conditional Object creation, only if name not already registered
    def __new__(cls, name, items=[], ign_bins=[], weight=1, at_least=1):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super(CoverCross, cls).__new__(CoverCross)

    def __init__(self, name, items=[], ign_bins=[], weight=1, at_least=1):
        if not name in coverage_db:
            CoverItem.__init__(self, name)
            if self._parent is None:
                raise Exception("CoverCross must have a parent (parent.CoverCross)")
            self._weight = weight
            self._at_least = at_least
            # equality operator is the defult ignore bins matching relation
            self._items = items

            bins_lists = []
            for cp_names in self._items:
                bins_lists.append(
                    coverage_db[cp_names].detailed_coverage.keys())

            # a map of cross-bins, key is a tuple of bins Cartesian product
            self._hits = dict.fromkeys(itertools.product(*bins_lists), 0)

            # remove ignore bins from _hits map if relation is true
            for x_bins in list(self._hits.keys()):
                for ignore_bins in ign_bins:
                    remove = True
                    for ii in range(0, len(x_bins)):
                        if ignore_bins[ii] is not None:
                            if (ignore_bins[ii] != x_bins[ii]):
                                remove = False
                    if remove and (x_bins in self._hits):
                        del self._hits[x_bins]

            self._size = self._weight * len(self._hits)
            self._parent._update_size(self._size)

    def __call__(self, f):
        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):

            current_coverage = self.coverage

            hit_lists = []
            for cp_name in self._items:
                hit_lists.append(coverage_db[cp_name]._new_hits)

            # a list of hit cross-bins, key is a tuple of bins Cartesian
            # product
            for x_bins_hit in list(itertools.product(*hit_lists)):
                if x_bins_hit in self._hits:
                    self._hits[x_bins_hit] += 1
                    # check bins callbacks
                    if x_bins_hit in self._bins_callbacks:
                        self._bins_callbacks[x_bins_hit]()

            # notify parent about new coverage level
            self._parent._update_coverage(self.coverage - current_coverage)

            # check threshold callbacks
            for ii in self._threshold_callbacks:
                if (ii > 100 * current_coverage / self.size and 
                    ii <= 100 * self.coverage / self.size):
                    self._threshold_callbacks[ii]()

            return f(*cb_args, **cb_kwargs)
        return _wrapped_function

    @property
    def coverage(self):
        coverage = self._size
        for ii in self._hits:
            if self._hits[ii] < self._at_least:
                coverage -= self._weight
        return coverage

    @property
    def detailed_coverage(self):
        return self._hits


class CoverCheck(CoverItem):
    """
    Class used to create coverage checks as decorators. It is a simplified 
    CoverPointwith defined 2 bins: "PASS" and "FAIL" and f_pass() and f_fail() 
    functions. 
    Syntax:
    @coverage.CoverCheck(name, f_fail, f_pass, weight, at_least)    
    Where:
    name - a CoverCheck path and name, defining its position in a coverage trie
    f_fail - a failure function, if returned true, a coverage level is set 0% 
             permanently
    f_pass - a pass function, if returned true coverage level is set 100% after 
             (at_least) hits
    weight - (optional) a CoverCheck weight (by default 1)
    at_least - (optional) defines how many times f_pass needs to be satisfied 
               (by default 1)
    Example:
    @coverage.CoverCheck(
      name = "top.parent.check", 
      f_fail = lambda x : x == 0, 
      f_pass = lambda x : x < 5)
    def decorated_fun(self, arg):
      ...
    A CoverCheck is satisfied (100% covered) when sampled arg < 5 and never 
    sampled arg == 0.
    A CoverCheck is failed (0% covered) when at least once sampled arg == 0.

    """
    # conditional Object creation, only if name not already registered
    def __new__(cls, name, f_fail, f_pass=None, weight=1, at_least=1):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super(CoverCheck, cls).__new__(CoverCheck)

    def __init__(self, name, f_fail, f_pass=None, weight=1, at_least=1):
        if not name in coverage_db:
            CoverItem.__init__(self, name)
            if self._parent is None:
                raise Exception("CoverCheck must have a parent (parent.CoverCheck)")
            self._weight = weight
            self._at_least = at_least
            self._f_pass = f_pass
            self._f_fail = f_fail
            self._size = weight
            self._hits = dict.fromkeys(["PASS", "FAIL"], 0)

            # determines whether decorated a bound method
            self._decorates_method = None
            # determines whether pass function is a bound method
            self._f_pass_is_method = None
            # determines whether fail function is a bound method
            self._f_fail_is_method = None
            self._parent._update_size(self._size)

    def __call__(self, f):
        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):

            # if pass function not defined always return True
            if self._f_pass is None:
                def dummy_f(*cb_args):
                    return True
                self._f_pass = dummy_f

            # for the first time only check if decorates method in the class
            if self._decorates_method is None:
                self._decorates_method = False
                for x in inspect.getmembers(cb_args[0]):
                    if '__func__' in dir(x[1]):
                        # compare decorated function name with class functions
                        self._decorates_method = f.__name__ == x[
                            1].__func__.__name__
                        if self._decorates_method:
                            break

            # for the first time only check if a pass/fail function is a method
            if self._f_pass_is_method is None and self._f_pass:
                self._f_pass_is_method = "self" in inspect.signature(
                    self._f_pass).parameters
            if self._f_fail_is_method is None:
                self._f_fail_is_method = "self" in inspect.signature(
                    self._f_fail).parameters

            current_coverage = self.coverage

            # may be False (failed), True (passed) or None (undetermined)
            passed = None

            # if function is bound then remove "self" from the arguments list
            if self._decorates_method ^ self._f_pass_is_method:
                passed = True if self._f_pass(*cb_args[1:]) else None
            else:
                passed = True if self._f_pass(*cb_args) else None

            if self._decorates_method ^ self._f_fail_is_method:
                passed = False if self._f_fail(*cb_args[1:]) else passed
            else:
                passed = False if self._f_fail(*cb_args) else passed

            if passed:
                self._hits["PASS"] += 1
            elif not passed:
                self._hits["FAIL"] += 1

            if passed is not None:

                # notify parent about new coverage level
                self._parent._update_coverage(self.coverage - current_coverage)

                # check threshold callbacks
                for ii in self._threshold_callbacks:
                    if (ii > 100 * current_coverage / self.size and 
                        ii <= 100 * self.coverage / self.size):
                        self._threshold_callbacks[ii]()

                # check bins callbacks
                if "PASS" in self._bins_callbacks and passed:
                    self._bins_callbacks["PASS"]()
                elif "FAIL" in self._bins_callbacks and not passed:
                    self._bins_callbacks["FAIL"]()

            return f(*cb_args, **cb_kwargs)
        return _wrapped_function

    @property
    def coverage(self):
        coverage = 0
        if self._hits["FAIL"] == 0 and self._hits["PASS"] > self._at_least:
            coverage = self._weight
        return coverage

    @property
    def detailed_coverage(self):
        return self._hits


def reportCoverage(logger, bins=False):
    """Prints sorted coverage with optional bins details"""
    sorted_cov = sorted(coverage_db, key=str.lower)
    for ii in sorted_cov:
        logger("   " * ii.count('.') + "%s : %s, coverage=%d, size=%d " % (
            ii,
            coverage_db[ii],
            coverage_db[ii].coverage,
            coverage_db[ii].size
        )
        )
        if (type(coverage_db[ii]) is not CoverItem) & (bins):
            for jj in coverage_db[ii].detailed_coverage:
                logger("   " * ii.count('.') + "   BIN %s : %s" % (
                    jj,
                    coverage_db[ii].detailed_coverage[jj]
                )
                )


def coverageSection(*coverItems):
    """
    Combines multiple coverage items into a single decorator.
    Example:
    my_coverage = coverage.coverageSection(
      coverage.CoverItem("x",...),
      coverage.CoverItem("y",...),
      ...
    )
    ...
    @my_coverage
    def decorated_fun(self, arg):
      ...
    """
    def _nested(*decorators):
        def _decorator(f):
            for dec in reversed(*decorators):
                f = dec(f)
            return f
        return _decorator

    return _nested(coverItems)
