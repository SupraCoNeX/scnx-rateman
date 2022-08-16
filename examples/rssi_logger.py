#!/usr/bin/python3

import asyncio
import sys

from rateman import RateMan
from rateman.parsing import parse_s32

from common import parse_aps, setup_argparser


# Our callback for 'rxs' status lines. The argument count (after ap) must match
# the number of fields separated by ';' in 'rxs' lines, i.e. 9 
def log_rssi(ap, phy, timestamp, type, mac, min_rssi, rssi0, rssi1, rssi2, rssi3):
    rssi = parse_s32(min_rssi)
    print(f"{ap.id} (c- [{mac}] at RSSI {rssi}")


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

    # add an rxs data callback
    rateman.add_data_callback(log_rssi, type="rxs")

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman.stop())
        print("DONE")

