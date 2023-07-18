__version__ = "0.1"

import sys

if sys.version_info[0] != 3 or sys.version_info[1] < 11:
    print(
        "RateMan requires Python 3.11! "
        f"You are running {sys.version_info[0]}.{sys.version_info[1]}",
        file=sys.stderr
    )
    sys.exit(1)

from .accesspoint import *
from .station import *
from .rateman import *
from .parsing import *
from .rate_control import *
from .exception import *