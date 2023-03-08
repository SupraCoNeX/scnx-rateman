# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import sys
import rateman
from common import setup_argparser

if __name__ == "__main__":
    arg_parser = setup_argparser()
    args = arg_parser.parse_args()
    aps = rateman.from_strings(args.accesspoints)
    save_data = True

    if args.ap_file:
        aps += rateman.from_file(args.ap_file)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for ap in aps:
        ap.default_rc_alg = args.rc_alg
        ap.default_rc_opts = {"filter": "EWMA"}

    rateman_obj=rateman.RateMan(aps,loop=loop)

    if save_data:
        file_handles = {}
        for ap in aps:
            file_handles[ap.name] = open(f"{ap.name}.csv", 'w')

        # add a simple print callback to collect the incoming data
        rateman_obj.add_raw_data_callback(
            lambda ap,line:file_handles[ap.name].write(f"{line}\n")
        )

    print("Running rateman...")

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(asyncio.wait([rateman_obj.stop()], timeout=5))
        if save_data:
            for _, file_handle in file_handles.items():
                file_handle.close()
        print("DONE")
