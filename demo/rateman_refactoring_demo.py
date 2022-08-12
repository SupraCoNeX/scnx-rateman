# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 17:28:38 2022

@author: pawarsp
"""
import rateman
import sys
import argparse
import asyncio

def parse_aps(apstrs):
    aps = []

    for apstr in apstrs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Invalid access point: '{apstr}'", file=sys.stderr)
            continue

        id = fields[0]
        addr = fields[1]

        try:
            rcd_port = int(fields[2])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(rateman.AccessPoint(id, addr, rcd_port))

    return aps

# Exec: python rateman.py minstrel_ht_user_space AP1:192.168.23.4 AP2:192.46.34.23 -A ../../demo/sample_ap_lists/local_test.csv
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "algorithm",
    type=str,
    choices=["minstrel_ht_kernel_space", "minstrel_ht_user_space"],
    default="minstrel_ht_kernel_space",
    help="Rate control algorithm to run.",
)
arg_parser.add_argument(
    "-A",
    "--ap-file",
    metavar="AP_FILE",
    type=str,
    help="Path to a csv file where each line contains information about an access point "
    + "in the format: ID,ADDR,RCDPORT.",
)
arg_parser.add_argument(
    "accesspoints",
    metavar="AP",
    nargs="*",
    type=str,
    help="Accesspoint to connecto to. Format: 'ID:ADDR:RCDPORT'. "
    + "RCDPORT is optional and defaults to 21059.",
)
args = arg_parser.parse_args()
aps = parse_aps(args.accesspoints)
if args.ap_file:
    aps += rateman.get_aps_from_file(args.ap_file)

if len(aps) == 0:
    print("ERROR: No accesspoints given", file=sys.stderr)
    sys.exit(1)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

print("Running rateman...")
rateman = rateman.RateMan(aps, rate_control_alg=args.algorithm, loop=loop)

# add a simple print callback to see the incoming data
rateman.taskman.add_data_callback(lambda ap, line: print(f"{ap.ap_id}> '{line}'"))

try:
    loop.run_forever()
except (OSError, KeyboardInterrupt):
    print("Stopping...")
finally:
    loop.run_until_complete(rateman.stop())
    print("DONE")