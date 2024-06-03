#!/usr/bin/env python

import asyncio
import sys
import rateman
import time

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger("rate_control_fail", args.verbose)
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

    # start 'rc_failing' rate control algorithm.
    # This will import from the rc_failing.py file.
    for ap in aps:
        for sta in ap.stations():
            loop.run_until_complete(sta.start_rate_control("rc_failing", {"fail_after_s": 3}))

    try:
        print("Running rateman... (Press CTRL+C to stop)")
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
