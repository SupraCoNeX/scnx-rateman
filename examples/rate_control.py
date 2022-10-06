# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 17:28:38 2022

@author: pawarsp
"""
import rateman
import sys
import argparse
import asyncio

# Exec: python rateman.py minstrel-ht-user-space AP1:192.168.1.1:22 AP2:192.168.200.1:22 -A ../../demo/sample_ap_lists/local_test.csv
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "-r",
    "--rc-alg",
    metavar="RC_ALG",
    type=str,
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
aps = rateman.parse_ap_strs(args.accesspoints)
if args.ap_file:
    aps += rateman.get_aps_from_file(args.ap_file)

if len(aps) == 0:
    print("ERROR: No accesspoints given", file=sys.stderr)
    sys.exit(1)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

rate_control_options = { 'multi_rate_retry': 'random,random;4,1'}
print("Running rateman...")
rateman = rateman.RateMan(
    aps, 
    loop=loop, 
    save_data=True, 
    rate_control_alg=args.rc_alg, 
    **rate_control_options,
)

# add a simple print callback to see the incoming data
rateman.taskman.add_raw_data_callback(
    lambda ap, fields: print(f"{ap.ap_id}> '{fields}'")
)

try:
    loop.run_forever()
except (OSError, KeyboardInterrupt):
    print("Stopping...")
finally:
    loop.run_until_complete(rateman.stop())
    print("DONE")
