#!/usr/bin/python3

import asyncio

from rateman import RateMan

from common import parse_aps, setup_argparser

if __name__ == "__main__":
    arg_parser = setup_argparser()
    args = arg_parser.parse_args()
    aps = parse_aps(args.accesspoints)

    if args.ap_file:
        aps += accesspoint.from_file(args.ap_file)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print("Running rateman...")
    rateman = RateMan(aps, rate_control_alg=args.algorithm, loop=loop)

    # add a simple print callback to see the raw incoming data
    rateman.add_raw_data_callback(lambda ap, line: print(f"{ap.id} > '{line}'"))

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman.stop())
        print("DONE")
