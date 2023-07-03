from importlib import import_module

from .exception import RateControlError

def load(rc_alg):
    try:
        rc = import_module(rc_alg)
        return (rc.configure, rc.run)
    except ImportError as e:
        raise RateControlError(rc_alg, "Failed to load module") from e
