import asyncio
import itertools
import rateman
import time


__all__ = ["configure", "run", "pause", "resume"]

"""
This file is a minimal rate control implementation cycling through a station's supported rates and
enabling each rate for a given duration. Moreover, this version of the rate control algorithm can be
paused and resumed.
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
    interval = rc_opts.get("interval_ms", 1000)

    # return what we'll need in run()
    return dict(sta=sta, interval=interval, paused=False)


# The run() function implements the core rate control logic and is expected to run indefinitely. It
# receives as arguments what configure() returned.
async def run(ctx):
    # cycle through all of the STA's supported rates, setting each rate for the duration of
    # interval_ms.
    for rate in itertools.cycle(ctx["sta"].supported_rates):

        # stop operation if the stop flag is set
        while ctx["paused"]:
            await asyncio.sleep(0.1)
            continue

        start = time.perf_counter_ns()

        ctx["sta"].logger.debug(f"Setting rate={rate} for {ctx['interval']} ms")

        # issue the rate control settings command
        await ctx["sta"].set_rates([rate], [1])

        elapsed_milliseconds = (time.perf_counter_ns() - start) / 1_000_000

        await asyncio.sleep((ctx["interval"] - elapsed_milliseconds) / 1000)


# The optional pause() function is called to halt a rate control algorithm without destroying its
# state. It receives the same argument as run().
async def pause(ctx):
    ctx["paused"] = True


# The optional resume() function is called to resume a paused rate control algorithm. It receives
# the same argument as run().
async def resume(ctx):
    ctx["paused"] = False
