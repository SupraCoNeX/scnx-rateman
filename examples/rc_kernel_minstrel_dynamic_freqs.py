# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import sys
import rateman
from datetime import datetime

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    log = setup_logger("kernel_minstrel_dynamic_freqs")
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

    for ap in aps:
        for sta in ap.stations():
            loop.run_until_complete(
                sta.start_rate_control(
                    "minstrel_ht_kernel_space",
                    {
                        "reset_rate_stats": True,
                        "update_freq": 10,
                        "sample_freq": 50
                    }
                )
            )

    # Only enable 'stats' events to observe the statistics updates on the remote device
    for ap in aps:
        loop.run_until_complete(ap.disable_events())
        loop.run_until_complete(ap.enable_events(radio="all", events=["txs", "stats"]))

    timestamps = {
        ap: {
            sta.mac_addr: None for sta in ap.stations()
        } for ap in aps
    }

    # add a callback to print the timestamp of incoming 'best_rates' events. These are emitted once
    # per stats update
    def print_stats_update_timestamp(ap, ev, context=None):
        fields = ev.split(";")
        if fields[2] == "best_rates":
            if timestamps[ap][fields[3]]:
                cur_ts = int(fields[1], 16) / 1_000_000
                old_ts = timestamps[ap][fields[3]]
                hz = 1000 / (cur_ts - old_ts)
                print(f"{fields[3]}: [STATS UPDATE] {hz:.2f} Hz")
                timestamps[ap][fields[3]] = cur_ts
            else:
                timestamps[ap][fields[3]] = int(fields[1], 16) / 1_000_000

    rm.add_raw_data_callback(print_stats_update_timestamp)

    try:
        print("Running rateman... (Press CTRL+C to stop)")
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
