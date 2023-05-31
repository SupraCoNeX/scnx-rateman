# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Rate Manager
======================================

Motivation
----------




"""


__version__ = "0.1"

import sys

if sys.version_info[0] != 3 or sys.version_info[1] < 11:
	print(
	    "SupraCoNeX Experimentor requires Python 3.11! "
	    f"You are running {sys.version_info[0]}.{sys.version_info[1]}",
	    file=sys.stderr
	)
	sys.exit(1)

from .rateman import *
from .accesspoint import *
from .station import *
from .parsing import *
from .rate_control import *
