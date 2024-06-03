#!/usr/bin/env python

import asyncio
import sys
import rateman
import time

from common import parse_arguments, setup_logger


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger("manual_mrr_setter_tpc", args.verbose)
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

    rc_started = False

    for ap in aps:
        # enable TPC for all radios which support it
        for radio in ap.radios:
            try:
                loop.run_until_complete(ap.set_feature(radio, "tpc", "1"))
                for sta in ap.stations(radio):
                    loop.run_until_complete(
                        sta.start_rate_control(
                            "manual_mrr_setter",
                            {"control_type": "tpc", "multi_rate_retry": "round_robin;1;19.0"},
                        )
                    )
                    rc_started = True
            except rateman.UnsupportedFeatureException as e:
                log.warning(f"{e}")
                continue

    # make sure we were able to start RC for at least one station, exit otherwise
    if not rc_started:
        print(
            "Unable to start RC. Maybe TPC is not supported or no station is associated?",
            file=sys.stderr,
        )
        loop.run_until_complete(rm.stop())
        sys.exit(1)

    # Enable 'txs' events so we can see our rate setting in action. Note, this requires traffic to
    # produce events. pinging the station across the wireless link can help with that.
    for ap in aps:
        loop.run_until_complete(ap.disable_events(events=["stats", "rxs", "tprc_echo"]))
        loop.run_until_complete(ap.enable_events(events=["txs"]))

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
