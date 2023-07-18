from importlib import import_module

from .exception import RateControlError

def load(rc_alg):
    try:
        mod = import_module(rc_alg)
        configure = getattr(mod, "configure", None)
        run = getattr(mod, "run", None)

        if not configure or not run:
            raise RateControlError(rc_alg, "Module does not expose 'configure' and 'run' functions")

        return (configure, run)
    except ImportError as e:
        raise RateControlError(rc_alg, "Failed to load module") from e
