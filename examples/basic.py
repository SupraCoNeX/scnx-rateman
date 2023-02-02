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

    if args.ap_file:
        aps += rateman.from_file(args.ap_file)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print("Running rateman...")
    rateman_obj = rateman.RateMan(aps, loop=loop)

    # add a simple print callback to see the raw incoming data
    rateman_obj.add_raw_data_callback(
        lambda ap, fields: print(f"{ap.name} > '{fields}'")
    )

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman_obj.stop())
        print("DONE")
