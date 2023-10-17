#!/usr/bin/env python

import asyncio
import sys
import rateman
from common import parse_arguments, setup_logger


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger("basic", args.verbose)
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

    # Enable only 'txs' and 'stats' events
    for ap in aps:
        loop.run_until_complete(ap.disable_events())
        loop.run_until_complete(ap.enable_events(events=["txs", "stats"]))

    # add a simple print callback to see the incoming data
    def print_event(ap, ev, context=None):
        print(f"{ap.name} > {ev}")

    rm.add_raw_data_callback(print_event)

    # run indefinitely
    try:
        print("Running rateman... (Press CTRL+C to stop)")
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
