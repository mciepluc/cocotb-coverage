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
Functional Coverage features.

Classes:

* :class:`CoverageDB` - singleton containing coverage database.
* :class:`CoverItem` - base class for coverage, corresponds to a covergroup,
  created automatically.
* :class:`CoverPoint` - a cover point with bins.
* :class:`CoverCross` - a cover cross of cover points.
* :class:`CoverCheck` - a cover point which checks only a pass/fail condition.

Functions:

* :func:`~.coverage_section` - allows for convenient definition of multiple
  coverage items and combines them into a single decorator.
* :func:`~.XML_merger` - merges coverage databases saved in XML format. 
"""

from functools import wraps
from collections import OrderedDict
import inspect
import operator
import itertools
import warnings
import copy
from xml.etree import ElementTree as et


class CoverageDB(dict):
    """ Class (singleton) containing coverage database.

    This is the coverage prefix tree (trie) containing all coverage objects
    with name string as a key (using dot as a stage separator). Coverage
    primitives may be accessed by string identificator. Example coverage trie
    is shown below:

    .. image:: coverstruct.png
        :scale: 60 %
        :align: center

    Examples:

    >>> CoverageDB()["top"] #access whole coverage under ``top``
    >>> CoverageDB()["top.b"] #access whole covergroup
    >>> CoverageDB()["top.b.cp1"] #access specific coverpoint
    """
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = dict.__new__(class_, *args, **kwargs)
        return class_._instance

    def report_coverage(self, logger, bins=False):
        """Print sorted coverage with optional bins details.

        Args:
            logger (func): a logger object.
            bins (bool): print bins details.

        """
        sorted_cov = sorted(self, key=str.lower)
        for ii in sorted_cov:
            logger("   " * ii.count('.') + "%s : %s, coverage=%d, size=%d " %
                   (ii, self[ii], self[ii].coverage, self[ii].size)
                   )
            if (type(self[ii]) is not CoverItem) & (bins):
                for jj in self[ii].detailed_coverage:
                    logger("   " * ii.count('.') + "   BIN %s : %s" %
                           (jj, self[ii].detailed_coverage[jj])
                           )

    def export_to_xml(self, xml_name='coverage.xml'):
        """Export coverage_db to xml document.

        Args:
            xml_name (str): output document name with .xml suffix
        """
        xml_db_dict = {}

        def create_top():
            attrib_dict = {'abs_name': 'top'}
            if 'top' in self:
                attrib_dict['size'] = str(self['top'].size)
                attrib_dict['coverage'] = str(self['top'].coverage)
                attrib_dict['cover_percentage'] = str(round(
                    self['top'].cover_percentage, 2))
            xml_db_dict['top'] = et.Element('top', attrib=attrib_dict)

        def create_element(name_elem, parent, name_elem_full):
            attrib_dict = {}
            prefix = '' if 'top' in self else 'top.'

            # Common attributes
            attrib_dict['size'] = str(self[name_elem_full].size)
            attrib_dict['coverage'] = str(self[name_elem_full].coverage)
            attrib_dict['cover_percentage'] = str(round(
                self[name_elem_full].cover_percentage, 2))
            attrib_dict['abs_name'] = prefix+name_elem_full
            if (type(self[name_elem_full]) is not CoverItem):
                attrib_dict['weight'] = str(self[name_elem_full].weight)
                attrib_dict['at_least'] = str(
                    self[name_elem_full].at_least)

            # Create element: xml_db_dict[a.b.c] = et(a.b (parent), c(element))
            xml_db_dict[name_elem_full] = et.SubElement(xml_db_dict[parent],
                                                        name_elem,
                                                        attrib=attrib_dict)

            # Create bins for CoverCross and CoverPoint
            if type(self[name_elem_full]) is not CoverItem:
                bin_count = 0
                # Database in format: key == bin_value, value == no_of_hits
                for key, value in self[name_elem_full].detailed_coverage.items():
                    attrib_dict.clear()
                    attrib_dict['bin_value'] = str(key)
                    attrib_dict['hits'] = str(value)
                    attrib_dict['abs_name'] = (prefix+name_elem_full
                                               +'.bin'+str(bin_count))
                    xml_db_dict[name_elem_full+'.bin'+str(bin_count)] = (
                        et.SubElement(xml_db_dict[name_elem_full],
                                      'bin'+str(bin_count),
                                      attrib=attrib_dict))
                    bin_count += 1

        # ======================== Function body ==============================
        create_top()
        for name_elem_full in self:
            if name_elem_full == 'top':
                pass
            else:
                name_list = name_elem_full.split('.')
                name_elem = name_list[-1]
                name_parent = '.'.join(name_list[:-1])
                if name_parent == '':
                    name_parent = 'top'
                create_element(name_elem, name_parent, name_elem_full)

        # update total coverage if there was no 'top' in coverage_db
        if xml_db_dict['top'].attrib == {'abs_name': 'top'}:
            top_size = 0
            top_coverage = 0
            for child in xml_db_dict['top'].getchildren():
                top_size += int(child.attrib['size'])
                top_coverage += int(child.attrib['coverage'])
                top_cover_percentage = round(top_coverage*100/top_size, 2)
            xml_db_dict['top'].set('size', str(top_size))
            xml_db_dict['top'].set('coverage', str(top_coverage))
            xml_db_dict['top'].set(
                'cover_percentage', str(top_cover_percentage))

        root = et.ElementTree(xml_db_dict['top']).getroot()
        _indent(root)
        et.ElementTree(xml_db_dict['top']).write(xml_name)

# global variable collecting coverage in a prefix tree (trie)
coverage_db = CoverageDB()
""" Instance of the :class:`CoverageDB`."""

class CoverItem(object):
    """Class used to describe coverage groups.

    ``CoverItem`` objects are created automatically. This is a base class for
    all coverage primitives (:class:`CoverPoint`, :class:`CoverCross` or
    :class:`CoverCheck`). It may be used as a base class for other,
    user-defined coverage types. 
    """

    def __init__(self, name):
        self._name = name
        self._size = 0
        self._coverage = 0
        self._parent = None
        self._children = []
        self._new_hits = []
        self._weight = 0
        self._at_least = 0

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
        """Update the parent coverage level as requested by derived classes. 
        """
        current_coverage = self._coverage
        self._coverage += coverage
        if self._parent is not None:
            self._parent._update_coverage(coverage)

        # notify callbacks
        for ii in self._threshold_callbacks:
            if (ii > 100 * current_coverage / self.size
                    and ii <= self.cover_percentage):
                self._threshold_callbacks[ii]()

    def _update_size(self, size):
        """Update the parent size as requested by derived classes. 
        """
        self._size += size
        if self._parent is not None:
            self._parent._update_size(size)

    def add_threshold_callback(self, callback, threshold):
        """Add a threshold callback to the :class:`CoverItem` or any its 
        derived class. 

        A callback is called (once) when the threshold is crossed, so that 
        coverage level of this particular cover group (or other object) exceeds 
        defined % value. 

        Args:
            callback (func): a callback function.
            threshold (int): a callback call threshold (% coverage). 

        Examples:

        >>> def notify_threshold():
        >>>     print("reached 50% coverage!")
        >>>
        >>> # add callback to the cover group
        >>> coverage_db["top.covergroup1"].add_threshold_callback(
        >>>   notify_threshold, 50
        >>> )
        >>> # add callback to the cover point
        >>> coverage_db["top.covergroup1.coverpoint4"].add_threshold_callback(
        >>>   notify_threshold, 50
        >>> )
        """
        self._threshold_callbacks[threshold] = callback

    def add_bins_callback(self, callback, bins):
        """Add a bins callback to the derived class of the :class:`CoverItem`.

        A callback is called (once) when a specific bin is covered. 

        Args:
            callback (func): a callback function.
            bins: a particular bin (type depends on bins type). 

        Examples:

        >>> def notify_bins():
        >>>     print("covered bin 'special case'")
        >>>
        >>> coverage_db["top.covergroup1.coverpoint5"].add_bins_callback(
        >>>   notify_bins, 'special case'
        >>> )
        """
        self._bins_callbacks[bins] = callback

    @property
    def size(self):
        """Return size of the coverage primitive.

        Size of the cover group (or other coverage primitive) is returned. This
        is a total number of bins associated with assigned weights. 

        Returns:
            int: size of the coverage primitive.
        """
        return self._size

    @property
    def coverage(self):
        """Return size of the covered bins in the coverage primitive.

        Number of the covered bins in cover group (or other coverage primitive) 
        is returned. This is a number of covered bins associated with assigned 
        weights. 

        Returns:
            int: size of the covered bins.
        """
        return self._coverage

    @property
    def cover_percentage(self):
        """Return coverage level of the coverage primitive.

        Percent of the covered bins in cover group (or other coverage 
        primitive) is returned. This is basically a :meth:`coverage()` divided
        by :meth:`size()` in %.

        Returns:
            float: percent of the coverage.
        """
        return 100 * self.coverage / self.size

    @property
    def detailed_coverage(self):
        """Return detailed coverage - full list of bins associated with number
        of hits. 

        A dictionary (bins) -> (number of hits) is returned. 

        Returns:
            dict: dictionary associating number of hits with a particular bins.
        """
        coverage = {}
        for child in self._children:
            coverage.append(child.detailed_coverage)
        return coverage

    @property
    def new_hits(self):
        """Return bins hit at last sampling event. Works only for objects 
        deriving from :class:`CoverItem`.

        Returns:
            list: list of the new bins (which have not been already covered)
            sampled at last sampling event.
        """
        return self._new_hits

    @property
    def weight(self):
        """Return weight of the coverage primitive. Works only for objects 
        deriving from :class:`CoverItem`.

        Returns:
            int: weight of the coverage primitive.
        """
        return self._weight

    @property
    def at_least(self):
        """Return ``at_least`` attribute of the coverage primitive. Works only 
        for objects deriving from :class:`CoverItem`.

        Returns:
            int: ``at_least`` attribute of the coverage primitive.
        """
        return self._at_least


class CoverPoint(CoverItem):
    """Class used to create coverage points as decorators. 

    This decorator samples members of the decorated function (its signature). 
    Sampling matches predefined bins according to the rule:
    ``rel(xf(args), bin) == True``

    Args:
        name (str): a ``CoverPoint`` path and name, defining its position in a 
            coverage trie.
        vname (str, optional): a name of the variable to be covered (use this 
            only when covering a *single* variable in the decorated function
            signature).
        xf (func, optional): a transformation function which transforms 
            arguments of the decorated function. If ``vname`` and ``xf`` are 
            not defined, matched is a single input argument (if only one 
            exists) or a tuple (if multiple exist). Note that the ``self`` 
            argument is *always* removed from the argument list. 
        bins (list): a list of bins objects to be matched. Note that for 
            non-trivial types, a ``rel`` must always be defined (or the 
            equality operator must be overloaded).
        rel (func, optional): a relation function which defines the bins 
            matching relation (by default, the equality operator ``==``).
        weight (int, optional): a ``CoverPoint`` weight (by default ``1``).
        at_least (int, optional): the number of hits per bins to be considered 
            as covered (by default ``1``).
        inj (bool, optional): "injection" feature, defines that more than a 
            single bin can be matched at one sampling (default ``False``).

    Example:

    >>> @coverage.CoverPoint( # cover (arg/2) < 1...5 (5 bins)
    ...     name = "top.parent.coverpoint1", 
    ...     xf = lambda x : x/2, 
    ...     rel = lambda x, y : x < y, 
    ...     bins = list(range(1, 5))
    ... )
    >>> @coverage.CoverPoint( # cover (arg) == 1...5 (5 bins)
    ...     name = "top.parent.coverpoint2", 
    ...     vname = "arg",
    ...     bins = list(range(1, 5))
    ... )
    >>> def decorated_func1(self, arg):
    ...     ...

    >>> @coverage.CoverPoint( # cover (arg1, arg2) == (1, 1) or (0, 0) (2 bins)
    ...     name = "top.parent.coverpoint3", 
    ...     bins = [(1, 1), (0, 0)]
    ... )
    >>> def decorated_func1(self, arg1, arg2):
    ...     ...
    """

    # conditional Object creation, only if name not already registered
    def __new__(cls, name, vname=None, xf=None, rel=None, bins=[], weight=1,
                at_least=1, inj=False):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super(CoverPoint, cls).__new__(CoverPoint)

    def __init__(self, name, vname=None, xf=None, rel=None, bins=[],
                 weight=1, at_least=1, inj=False):
        if not name in coverage_db:
            CoverItem.__init__(self, name)
            if self._parent is None:
                raise Exception("CoverPoint must have a parent \
                                 (parent.CoverPoint)")

            self._transformation = xf
            self._vname = vname

            # equality operator is the default bins matching relation
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
                # if vname defined, match it to the decroated function args
                else:
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
                        self._decorates_method = \
                            f.__name__ == x[1].__func__.__name__
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
                if (ii > 100 * current_coverage / self.size
                        and ii <= 100 * self.coverage / self.size):
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


class CoverCross(CoverItem):
    """Class used to create coverage crosses as decorators.

    This decorator samples members of the decorated function (its signature). 
    It matches tuples cross-bins which are Cartesian products of bins defined 
    in :class:`CoverPoints <CoverPoint>` (items).

    Args:
        name (str): a ``CoverCross`` path and name, defining its position in a 
            coverage trie.
        items (list): a list of :class:`CoverPoints <CoverPoint>` by names, 
            to create a Cartesian product of cross-bins.
        ign_bins (list, optional): a list of bins to be ignored.
        weight (int, optional): a ``CoverCross`` weight (by default ``1``).
        at_least (int, optional): the number of hits per bin to be considered 
            as covered (by default ``1``).

    Example:

    >>> @coverage.CoverPoint(
    ...     name = "top.parent.coverpoint1", 
    ...     xf = lambda x, y: x, 
    ...     bins = range(1, 5) # 5 bins in total
    ... )
    >>> @coverage.CoverPoint(
    ...     name = "top.parent.coverpoint2",
    ...     xf = lambda x, y: y, 
    ...     bins = range(1, 5) # 5 bins in total
    ... )
    >>> @coverage.CoverCross(
    ...     name = "top.parent.covercross", 
    ...     items = ["top.parent.coverpoint1", "top.parent.coverpoint2"],
    ...     ign_bins = [(1, 1), (5, 5)], # 5x5 - 2 = 23 bins in total
    ... )
    >>> def decorated_func(self, arg_a, arg_b):
    >>> # bin from the bins list [(1, 2), (1, 3)...(5, 4)] will be matched 
    >>> # when a tuple (x=arg_a, y=arg_b) was sampled at this function call.
    ...     ...
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
                raise Exception("CoverCross must have a parent \
                                 (parent.CoverCross)")

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
                if (ii > 100 * current_coverage / self.size
                        and ii <= 100 * self.coverage / self.size):
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
    """Class used to create coverage checks as decorators. 

    It is a simplified :class:`CoverPoint` with defined 2 bins:
    *PASS* and *FAIL* and ``f_pass()`` and ``f_fail()`` functions. 

    Args:
        name (str): a ``CoverCheck`` path and name, defining its position in a 
            coverage trie.
        f_fail: a failure condition function - if it returns ``True``, them
            coverage level is set to ``0`` permanently.
        f_pass: a pass condition function - if it returns ``True``, the 
            coverage level is set to ``weight`` after ``at_least`` hits. 
        weight (int, optional): a ``CoverCheck`` weight (by default ``1``).
        at_least (int, optional): the number of hits of the ``f_pass`` function 
            to consider a particular ``CoverCheck`` as covered. 

    Example:

    >>> @coverage.CoverCheck(
    ...     name = "top.parent.check", 
    ...     f_fail = lambda x : x == 0, 
    ...     f_pass = lambda x : x < 5)
    >>> def decorated_fun(self, arg):
    >>> # CoverCheck is 100% covered when (arg < 5) and never (arg == 0) was 
    >>> # sampled. CoverCheck is set to 0 unconditionally when at least once
    >>> # (arg == 0) was sampled.
    ...     ...
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
                raise Exception("CoverCheck must have a parent \
                                 (parent.CoverCheck)")
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
            elif passed is not None:
                self._hits["FAIL"] += 1

            if passed is not None:

                # notify parent about new coverage level
                self._parent._update_coverage(self.coverage - current_coverage)

                # check threshold callbacks
                for ii in self._threshold_callbacks:
                    if (ii > 100 * current_coverage / self.size
                            and ii <= 100 * self.coverage / self.size):
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
        if self._hits["FAIL"] == 0 and self._hits["PASS"] >= self._at_least:
            coverage = self._weight
        return coverage

    @property
    def detailed_coverage(self):
        return self._hits


def coverage_section(*coverItems):
    """Combine multiple coverage items into a single decorator.

    Args:
        *coverItems ((multiple) :class:`CoverItem`): coverage primitives to be
            combined.

    Example:

    >>> my_coverage = coverage.coverageSection(
    ...     coverage.CoverPoint("x", ...),
    ...     coverage.CoverPoint("y", ...),
    ...     coverage.CoverCross("z", ...),
    ...     ...
    ... )
    >>>
    >>> @my_coverage
    >>> def decorated_fun(self, arg):
    ...     ...
    """
    def _nested(*decorators):
        def _decorator(f):
            for dec in reversed(*decorators):
                f = dec(f)
            return f
        return _decorator

    return _nested(coverItems)

### XML coverage database functions

# XML pretty print format - ElementTree lib extension
def _indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            _indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def XML_merger(merged_xml_name, *xmls):
    """ Function used for merging coverage metrics in XML format.

    Args:
        merged_xml_name (str): output XML name with .xml suffix
        *xmls ((multiple) str): comma separated XML names with .xml suffix

    Example:

    >>> XML_merger('merged.xml', 'one.xml', 'other.xml') # merge one and other
    """
    roots = [et.parse(xml).getroot() for xml in xmls]
    merged_root = copy.deepcopy(roots[0])
    # abs name to element mapping - merged items
    name_to_elem = {el.attrib['abs_name']: el for el in merged_root.iter()}

    def combine():
        for root in roots[1:]:
            combine_element(root)
        _indent(merged_root) # pretty print format
        et.ElementTree(merged_root).write(merged_xml_name)

    def combine_element(root):
        # Elements not present in merged items
        new_elements = [elem for elem in root.iter()
                        if elem.attrib['abs_name'] not in name_to_elem.keys()]
        # Sort descending
        new_elements.sort(key=lambda _: _.attrib['abs_name'].count('.'))
        # Bin list to be updated w/o bins not present in the merged
        bin_list = [elem for elem in root.iter() if 'bin' in elem.tag
                    and elem not in new_elements]

        def get_parent(abs_name):
            return '.'.join(abs_name.split('.')[:-1])

        def update_parent(name, bin_update=False, new_element_update=False,
                          coverage_update=0, size_update=0):
            parent_name = get_parent(name)
            if parent_name == '':
                return # Top reached
            else:
                if new_element_update:
                    coverage_update = int(
                        name_to_elem[name].attrib['coverage'])
                    size_update = int(
                        name_to_elem[name].attrib['size'])
                elif bin_update:
                    coverage_update = int(
                        name_to_elem[parent_name].attrib['weight'])

                # Update current parent
                name_to_elem[parent_name].attrib['coverage'] = str(int(
                    name_to_elem[parent_name].attrib['coverage'])
                    + coverage_update)
                name_to_elem[parent_name].attrib['size'] = str(int(
                    name_to_elem[parent_name].attrib['size'])+size_update)
                name_to_elem[parent_name].attrib['cover_percentage'] = str(
                    round((int(name_to_elem[parent_name].attrib['coverage'])
                    *100/int(name_to_elem[parent_name].attrib['size'])), 2))
                # Recursively update parents
                update_parent(parent_name, False, False,
                              coverage_update, size_update)

        # Merge function body
        # Extend merged with new elements in descending order
        for elem in new_elements:
            abs_name = elem.attrib['abs_name']
            parent_name = get_parent(abs_name)
            name_to_elem[abs_name] = et.SubElement(
                name_to_elem[parent_name], elem.tag, attrib=elem.attrib)
            if 'bin' not in elem.tag:
                update_parent(name=abs_name, bin_update=False, 
                              new_element_update=True)

        # Update bins already present in the XML
        for bin_element in bin_list:
            hits = int(bin_element.attrib['hits'])
            if hits > 0:
                abs_name = bin_element.attrib['abs_name']
                hits_orig = int(name_to_elem[abs_name].attrib['hits'])
                # Update the bin value
                name_to_elem[abs_name].attrib['hits'] = str(hits+hits_orig)
                # Check if upstream needs updating
                parent_name = get_parent(abs_name)
                parent_hits_threshold = int(
                    name_to_elem[parent_name].attrib['at_least'])
                if (hits_orig < parent_hits_threshold
                        and hits_orig+hits >= parent_hits_threshold):
                    update_parent(name=abs_name, bin_update=True,
                                  new_element_update=False)
    
    # Call combine function to merge XMLs
    combine()

# deprecated

def reportCoverage(logger, bins=False):
    """.. deprecated:: 1.0"""
    warnings.warn(
        "Function reportCoverage() is deprecated, use "
        + "coverage_db.report_coverage() instead"
    )
    coverage_db.report_coverage(logger, bins)


def coverageSection(*coverItems):
    """.. deprecated:: 1.0"""
    warnings.warn(
        "Function coverageSection() is deprecated, use coverage_section() instead"
    )
    return coverage_section(*coverItems)


