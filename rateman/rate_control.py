from importlib import import_module

from .exception import RateControlError

def load(rc_alg):
    try:
        return import_module(rc_alg).start
    except ImportError as e:
        raise RateControlError(rc_alg, "Failed to load module") from e
