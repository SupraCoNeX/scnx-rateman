#!/usr/bin/env python

import asyncio
import sys
import rateman
import time

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger("rate_control_pause_resume", args.verbose)

    # create rateman.AccessPoint objects
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

    # Fail if any AP connection could not be established
    for ap in aps:
        if not ap.connected:
            sys.exit(1)

    # start 'rc_pause_resume' rate control algorithm.
    # This will import from the rc_pause_resume.py file.
    for ap in aps:
        loop.run_until_complete(ap.enable_tprc_echo(True))
        for sta in ap.stations():
            loop.run_until_complete(
                sta.start_rate_control("rc_pause_resume", {"interval_ms": 1000})
            )

    # Enable 'txs' events so we can see our rate setting in action. Note, this requires traffic to
    # produce events. pinging the station across the wireless link can help with that.
    for ap in aps:
        loop.run_until_complete(ap.disable_events())
        loop.run_until_complete(ap.enable_events(events=["txs", "stats"]))

    # add a simple print callback to see the txs events
    def print_event(ap, ev, context=None):
        print(f"{ap.name} > {ev}")

    rm.add_raw_data_callback(print_event)

    try:
        print("Running rateman... (Press CTRL+C to stop)")
        while True:
            # Let everything run for 5s
            loop.run_until_complete(asyncio.sleep(5))

            # Pause the RC algorithms
            for ap in aps:
                for sta in ap.stations():
                    loop.run_until_complete(sta.pause_rate_control())

            # Wait for 3s
            loop.run_until_complete(asyncio.sleep(3))

            # Resume the RC algorithms
            for ap in aps:
                for sta in ap.stations():
                    loop.run_until_complete(sta.resume_rate_control())
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
