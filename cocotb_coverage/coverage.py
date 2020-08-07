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
* :func:`~.merge_coverage` - merges coverage files in XML or YAML format. 
"""

from functools import wraps
from collections import OrderedDict
import inspect
import operator
import itertools
import warnings
import copy
import threading

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
    _lock = threading.Lock()

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            with class_._lock:
                if not isinstance(class_._instance, class_):
                    class_._instance = dict.__new__(class_, *args, **kwargs)
        return class_._instance

    def report_coverage(self, logger, bins=False, node=""):
        """Print sorted coverage with optional bins details.

        Args:
            logger (func): a logger object.
            bins (bool, optional): print bins details.
            node (str, optional): starting node of the coverage trie.
        """
        sorted_cov = sorted(self, key=str.lower)
        for ii in filter(lambda _ : _.startswith(node), sorted_cov):
            logger("   " * ii.count('.') + "%s : %s, coverage=%d, size=%d " %
                   (ii, self[ii], self[ii].coverage, self[ii].size)
                   )
            if (type(self[ii]) is not CoverItem) & (bins):
                for jj in self[ii].detailed_coverage:
                    logger("   " * ii.count('.') + "   BIN %s : %s" %
                           (jj, self[ii].detailed_coverage[jj])
                           )

    def export_to_yaml(self, filename='coverage.yml'):
        """Export coverage_db to YAML document.

        Args:
            filename (str): output document name with .yml suffix
        """
        import yaml

        export_data = {}
        for name_elem_full in sorted(self, key=str.lower):

            attrib_dict = {}
            attrib_dict['type'] = str(type(self[name_elem_full]))
            attrib_dict['size'] = self[name_elem_full].size
            attrib_dict['coverage'] = self[name_elem_full].coverage
            attrib_dict['cover_percentage'] = round(self[name_elem_full].cover_percentage, 2)

            if (type(self[name_elem_full]) is not CoverItem):
                attrib_dict['weight'] = self[name_elem_full].weight
                attrib_dict['at_least'] = self[name_elem_full].at_least

                bins = []
                hits = []

                for key, value in self[name_elem_full].detailed_coverage.items():
                    if hasattr(key, '__iter__'): #convert iterables to string
                        key = str(key)
                    bins.append(key)
                    hits.append(value)

                attrib_dict['bins:_hits'] = dict(zip(bins, hits))

            export_data[name_elem_full] = attrib_dict

        with open(filename, 'w') as outfile:
            yaml.dump(export_data, outfile, default_flow_style=False)

    def export_to_xml(self, filename='coverage.xml'):
        """Export coverage_db to xml document.

        Args:
            filename (str): output document name with .xml suffix
        """
        from xml.etree import ElementTree as et
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
                # Database in format: key == bin, value == no_of_hits
                for key, value in self[name_elem_full].detailed_coverage.items():
                    attrib_dict.clear()
                    attrib_dict['bin'] = str(key)
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
            for child in xml_db_dict['top']:
                top_size += int(child.attrib['size'])
                top_coverage += int(child.attrib['coverage'])
                top_cover_percentage = round(top_coverage*100/top_size, 2)
            xml_db_dict['top'].set('size', str(top_size))
            xml_db_dict['top'].set('coverage', str(top_coverage))
            xml_db_dict['top'].set(
                'cover_percentage', str(top_cover_percentage))

        root = et.ElementTree(xml_db_dict['top']).getroot()
        _indent(root)
        et.ElementTree(xml_db_dict['top']).write(filename)

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
        of hits. If labels are assigned to bins, labels are returned instead
        of bins values.

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
        bins_labels (list, optional): a list of labels (str) associated with
            defined bins. Both lists lengths must match.
        rel (func, optional): a relation function which defines the bins 
            matching relation (by default, the equality operator ``==``).
        weight (int, optional): a ``CoverPoint`` weight (by default ``1``).
        at_least (int, optional): the number of hits per bins to be considered 
            as covered (by default ``1``).
        inj (bool, optional): "injection" feature, defines that more than a 
            single bin can be matched at one sampling (default ``False``).

    Example:

    >>> @coverage.CoverPoint( # cover (arg/2) < 1 ... 4 (4 bins)
    ...     name = "top.parent.coverpoint1", 
    ...     xf = lambda x : x/2, 
    ...     rel = lambda x, y : x < y, 
    ...     bins = list(range(5))
    ... )
    >>> @coverage.CoverPoint( # cover (arg) == 1 ... 4 (4 bins)
    ...     name = "top.parent.coverpoint2", 
    ...     vname = "arg",
    ...     bins = list(range(5))
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
    def __new__(cls, name, vname=None, xf=None, rel=None, bins=[],
                bins_labels=None, weight=1, at_least=1, inj=False):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super(CoverPoint, cls).__new__(CoverPoint)

    def __init__(self, name, vname=None, xf=None, rel=None, bins=[],
                 bins_labels=None, weight=1, at_least=1, inj=True):
        if not name in coverage_db:
            CoverItem.__init__(self, name)
            if self._parent is None:
                raise Exception("CoverPoint must have a parent \
                                 (parent.CoverPoint)")

            if (bins_labels is not None) and (len(bins_labels) != len(bins)):
                raise Exception("Length of bins and bins_labels must be \
                                 equal")

            self._bins_labels = bins_labels

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

            #make a map assigning label to the bin
            if self._bins_labels is not None:
                self._labels_bins = dict(zip(bins, bins_labels))

            # determines whether decorated a bound method
            self._decorates_method = None
            # determines whether transformation function is a bound method
            self._trans_is_method = None
            self._parent._update_size(self._size)

            self._new_hits = []  # list of bins hit per single function call

    def __call__(self, f):
        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):

            if len(cb_kwargs) > 0:
                raise Exception("Use of keyword args in sampling function call is not supported.")

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
            for bin in self._hits:
                if self._relation(result, bin):
                    self._hits[bin] += 1
                    if self._bins_labels is not None:
                        self._new_hits.append(self._labels_bins[bin])
                    else:
                        self._new_hits.append(bin)
                    # check bins callbacks
                    if bin in self._bins_callbacks:
                        self._bins_callbacks[bin]()
                    # if injective function, continue through all bins
                    if self._injection:
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
        if self._bins_labels is not None:
            return dict(zip(self._bins_labels, list(self._hits.values())))
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
    ...     bins = list(range(5)) # 4 bins in total
    ... )
    >>> @coverage.CoverPoint(
    ...     name = "top.parent.coverpoint2",
    ...     xf = lambda x, y: y, 
    ...     bins = list(range(5)) # 4 bins in total
    ... )
    >>> @coverage.CoverCross(
    ...     name = "top.parent.covercross", 
    ...     items = ["top.parent.coverpoint1", "top.parent.coverpoint2"],
    ...     ign_bins = [(1, 1), (4, 4)], # 4x4 - 2 = 14 bins in total
    ... )
    >>> def decorated_func(self, arg_a, arg_b):
    >>> # bin from the bins list [(1, 2), (1, 3)...(4, 3)] will be matched 
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
            for x_bin in list(self._hits.keys()):
                for ignore_bins in ign_bins:
                    remove = True
                    for ii in range(0, len(x_bin)):
                        if ignore_bins[ii] is not None:
                            if (ignore_bins[ii] != x_bin[ii]):
                                remove = False
                    if remove and (x_bin in self._hits):
                        del self._hits[x_bin]

            self._size = self._weight * len(self._hits)
            self._parent._update_size(self._size)

    def __call__(self, f):
        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):

            if len(cb_kwargs) > 0:
                raise Exception("Use of keyword args in sampling function call is not supported.")

            current_coverage = self.coverage

            hit_lists = []
            for cp_name in self._items:
                hit_lists.append(coverage_db[cp_name]._new_hits)

            # a list of hit cross-bins, key is a tuple of bins Cartesian
            # product
            for x_bin_hit in list(itertools.product(*hit_lists)):
                if x_bin_hit in self._hits:
                    self._hits[x_bin_hit] += 1
                    # check bins callbacks
                    if x_bin_hit in self._bins_callbacks:
                        self._bins_callbacks[x_bin_hit]()

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
        f_fail: a failure condition function - if it returns ``True``, the
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

            if len(cb_kwargs) > 0:
                raise Exception("Use of keyword args in sampling function call is not supported.")

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

def merge_coverage(logger, merged_file_name, *files):
    """ Function used for merging coverage metrics in XML and YAML format.

    Args:
        logger (func): a logger function
        merged_file_name (str): output filename
        *files ((multiple) str): comma separated filenames to merge coverage from

    Example:

    >>> merge_coverage('merged.xml', 'one.xml', 'other.xml') # merge one and other
    """
    from xml.etree import ElementTree as et
    import yaml

    l = len(files)
    if l == 0:
        raise ValueError('Coverage merger got no files to merge')

    def try_to_parse(parser_func, f, on_error):
        try:
            parser_func(f)
            return True
        except on_error:
            return False

    def is_xml(f):
        return try_to_parse(et.parse, f, et.ParseError)

    def is_yaml(f):
        return try_to_parse(yaml.safe_load, f, yaml.YAMLError)

    if is_xml(files[0]):
        filetype = 'xml'
        dbs = [et.parse(f).getroot() for f in files]
        logger(f'XML fileformat detected')

    elif is_yaml(files[0]):
        filetype = 'yaml'
        def load_yaml(filename, logger):
            with open(filename, 'r') as stream:
                try:
                    yaml_parsed = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    logger(exc)   
            return yaml_parsed
        dbs = [load_yaml(f, logger) for f in files]
        logger(f'YAML fileformat detected')

    else:
        raise ValueError('Coverage merger: unrecognized file format, provide yaml or xml')

    merged_db = dbs[0]

    def merge():
        for db in dbs[1:]:
            merge_element(db)
        logger(f'Merged {l} {"file" if l==1 else "files"}')
        if filetype == 'xml':
            _indent(merged_db)
            et.ElementTree(merged_db).write(merged_file_name)    
        else:
            with open(merged_file_name, 'w') as outfile:
                yaml.dump(merged_db, outfile, default_flow_style=False)
        logger(f'Saving coverage database as {merged_file_name}')

    def merge_element(db):
        if filetype == 'xml':
            pre_merge_db_dict = {elem.attrib['abs_name']: elem for elem in merged_db.iter()}
            name_to_elem = {el.attrib['abs_name']: el for el in merged_db.iter()}
            # Elements to be added, sort descending
            new_elements = [elem for elem in db.iter()
                            if elem.attrib['abs_name'] not in name_to_elem.keys()]
            new_elements.sort(key=lambda _: _.attrib['abs_name'].count('.'))
            # Bins that will be updated
            items_to_update = [elem for elem in db.iter() if 'bin' in elem.tag
                               and elem not in new_elements] 
        else:
            pre_merge_db_keys = list(merged_db.keys())
            new_elements = [elem_key for elem_key in db if elem_key not in merged_db]
            # Elements with bins that will be updated
            items_to_update = [elem_key for elem_key in db 
                             if 'bins:_hits' in list(db[elem_key].keys())
                             and elem_key not in new_elements]

        def get_parent_name(abs_name):
            return '.'.join(abs_name.split('.')[:-1])

        if filetype == 'xml':
            def update_parent(name, bin_update=False, new_element_update=False,
                              coverage_upd=0, size_upd=0,):
                parent_name = get_parent_name(name)
                if parent_name == '':
                    return
                else:
                    if new_element_update:
                        coverage_upd = int(
                            name_to_elem[name].attrib['coverage'])
                        size_upd = int(
                            name_to_elem[name].attrib['size'])
                    elif bin_update:
                        coverage_upd = int(
                            name_to_elem[parent_name].attrib['weight'])
                        size_upd = 0

                    # Update current parent
                    name_to_elem[parent_name].attrib['coverage'] = str(int(
                        name_to_elem[parent_name].attrib['coverage'])
                        + coverage_upd)
                    name_to_elem[parent_name].attrib['size'] = str(int(
                        name_to_elem[parent_name].attrib['size'])+size_upd)
                    name_to_elem[parent_name].attrib['cover_percentage'] = str(
                        round((int(name_to_elem[parent_name].attrib['coverage'])
                        *100/int(name_to_elem[parent_name].attrib['size'])), 2))
                    # Recursively update parents
                    update_parent(parent_name, False, False, coverage_upd,
                                  size_upd)
        else:
            def update_parent(name, coverage_upd, size_upd=0):
                parent = get_parent_name(name)
                if parent == '':
                    return
                else:
                    coverage = merged_db[parent]['coverage']
                    size = merged_db[parent]['size']
                    merged_db[parent]['coverage'] = coverage + coverage_upd
                    if size_upd != 0:
                        merged_db[parent]['size'] = size + size_upd
                    merged_db[parent]['cover_percentage'] = round(merged_db[parent]['coverage']*100/merged_db[parent]['size'], 2)
                    # Update up to the root
                    update_parent(parent, coverage_upd, size_upd)

        for elem in new_elements:
            # Update parents only once per new cg/cp
            if filetype == 'xml':
                abs_name = elem.attrib['abs_name']
                parent_name = get_parent_name(abs_name)
                name_to_elem[abs_name] = et.SubElement(
                    name_to_elem[parent_name], elem.tag, attrib=elem.attrib)
                if parent_name in pre_merge_db_dict:
                    update_parent(name=abs_name, bin_update=False, 
                                  new_element_update=True)
            else:
                parent_name = get_parent_name(elem)
                if elem not in merged_db.keys():
                    merged_db[elem] = db[elem]
                if parent_name in pre_merge_db_keys:
                    update_parent(elem, db[elem]['coverage'], db[elem]['size'])

        # Update cps with bins / bins from the new db
        for elem in items_to_update:
            if filetype == 'xml':
                hits = int(elem.attrib['hits'])
                if hits > 0:
                    abs_name = elem.attrib['abs_name']
                    hits_orig = int(name_to_elem[abs_name].attrib['hits'])
                    # Update the bin value
                    name_to_elem[abs_name].attrib['hits'] = str(hits+hits_orig)
                    # Check if upstream needs updating
                    parent_name = get_parent_name(abs_name)
                    parent_hits_threshold = int(
                        name_to_elem[parent_name].attrib['at_least'])
                    if (hits_orig < parent_hits_threshold
                        and hits_orig+hits >= parent_hits_threshold):
                        update_parent(name=abs_name, bin_update=True,
                                      new_element_update=False)
            else:
                new_hits_cnt = 0
                weight = merged_db[elem]['weight']
                at_least = merged_db[elem]['at_least']
                for bin_name, hits in db[elem]['bins:_hits'].items():
                    hits_orig = merged_db[elem]['bins:_hits'][bin_name]
                    if (hits_orig < at_least and hits_orig+hits >= at_least):
                        new_hits_cnt += 1
                    merged_db[elem]['bins:_hits'][bin_name] += hits
                if new_hits_cnt > 0:
                    coverage_upd = weight*new_hits_cnt
                    merged_db[elem]['coverage'] = merged_db[elem]['coverage']+coverage_upd
                    merged_db[elem]['cover_percentage'] = round(
                        merged_db[elem]['coverage']*100/merged_db[elem]['size'], 2)
                    update_parent(elem, coverage_upd) # update cover recursively 

    merge()

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

