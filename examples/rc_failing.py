import asyncio
import itertools
import rateman
import time


__all__ = ["configure", "run"]

"""
This file is a minimal rate control implementation cycling through a station's supported rates and
enabling each rate for a given duration.
"""


# The configure() function is expected to initialize the rate control scheme and configure the
# station to be controlled accordingly. In our case, we enable manual rate control mode and parse
# the interval at which the rate selection is to be updated. We return handles to the station object
# and the parsed interval, because we'll need both in run().
async def configure(sta: rateman.Station, **rc_opts: dict) -> object:
    # enable manual rate control for the station
    await sta.set_manual_rc_mode(True)
    await sta.set_manual_tpc_mode(False)

    # parse rc options
    interval = rc_opts.get("fail_after_s", 1)

    # return what we'll need in run()
    return (sta, interval)


# The run() function implements the core rate control logic and is expected to run indefinitely. It
# receives as arguments what configure() returned.
async def run(args):
    sta = args[0]
    interval = args[1]
    log = sta.logger

    await asyncio.sleep(interval)

    raise TimeoutError
