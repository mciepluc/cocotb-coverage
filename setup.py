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


from setuptools import setup
from setuptools import find_packages

import cocotb_coverage
version = cocotb_coverage.__version__

from os import path

def read_file(fname):
    return open(path.join(path.dirname(__file__), fname)).read()

setup(
    name='cocotb-coverage',
    version=version,
    description='Functional Coverage and Constrained Randomization Extensions for Cocotb',
    url='https://github.com/mciepluc/cocotb-coverage',
    license='BSD',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='Marek Cieplucha',
    author_email='',
    packages=find_packages(),
    install_requires= ['cocotb', 'python-constraint', 'pyyaml'],
    python_requires=">=3.3",
    platforms='any',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
