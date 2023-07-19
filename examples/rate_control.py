# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import sys
import rateman
import time

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    log = setup_logger("rate_control")
    args = parse_arguments()
    aps = rateman.from_strings(args.accesspoints, logger=log)

    if args.ap_file:
        aps += rateman.from_file(args.ap_file, logger=log)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    # create asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # create rateman object
    rm = rateman.RateMan(loop=loop, logger=log)

    # add APs to rateman
    for ap in aps:
        rm.add_accesspoint(ap)

    # establish connections and set up state
    loop.run_until_complete(rm.initialize())

    # start 'example_rc' rate control algorithm. This will import from the example_rc.py file.
    for ap in aps:
        for sta in ap.get_stations():
            loop.run_until_complete(sta.start_rate_control("example_rc", { "interval_ms": 1000 }))

    # Enable 'txs' events so we can see our rate setting in action. Note, this requires traffic to
    # produce events. pinging the station across the wireless link can help with that.
    for ap in aps:
        loop.run_until_complete(ap.disable_events())
        loop.run_until_complete(ap.enable_events(["txs"]))

    # add a simple print callback to see the txs events
    def print_event(ap, ev, context=None):
        print(f"{ap.name} > {ev}")

    rm.add_raw_data_callback(print_event)

    try:
        print("Running rateman... (Press CTRL+C to stop)")
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
