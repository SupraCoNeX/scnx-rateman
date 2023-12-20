#!/usr/bin/env python

import asyncio
import sys
import rateman
import time

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger("py_minstrel_ht_blues", args.verbose)
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

    file_handles = {}

    def log_event(ap, ev, context):
        context.write(f"{ev}\n")

    for ap in aps:
        file_handles[ap.name] = open(f"{ap.name}.csv", "w")
        rm.add_raw_data_callback(log_event, file_handles[ap.name])

        for sta in ap.stations():
            loop.run_until_complete(
                sta.start_rate_control(
                    "py_minstrel_ht",
                    {
                        "filter": "Butterworth",
                        "reset_rate_stats": True,
                        "kern_sample_table": True,
                        "tpc": {
                            "mode": "blues",
                            "ref_pwr": 11,
                            "pwr_inc": 3,
                            "pwr_dec": 1,
                            "power_sample_interval_ms": 80,
                            "inc_prob_tol": 0.2,
                            "dec_prob_tol": 0.1,
                            "falbck_prob": 0.3,
                            "opt_pwr_offset": 1,
                            "ref_prob_thres": 1,
                            "weight": 1,
                            "sample_update_thresh": 8,
                            "opt_update_thresh": 15,
                            "outdate_stats": False,
                        },
                    },
                )
            )

    # Enable 'txs' events so we can see our rate setting in action. Note, this requires traffic to
    # produce events. pinging the station across the wireless link can help with that.
    for ap in aps:
        loop.run_until_complete(ap.disable_events())
        loop.run_until_complete(ap.enable_events(events=["txs", "rxs"]))

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
        for _, file_handle in file_handles.items():
            file_handle.close()
        print("DONE")
