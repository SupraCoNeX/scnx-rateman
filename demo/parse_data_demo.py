# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Demo for parsing data (TXS and RCSTATS) into a .csv file per AP
----------------

This demo script illustrates the basic use of the RateManager package to 
parse data from multiple APs into designated .csv files. Data denotes TX Status
Rate Control Statistics piped using the 'phyX;start;stats;txs' command with 
minstrel-rcd. 

Run the demo script in the terminal using,

python parse_data_demo.py


RateMan is stopped within the terminal, observe the print statements.


"""

import rateman
import sys
import argparse
import time
import logging
import asyncio

def get_path_arg(parser):
    """
    Parses path argument provided in the exec command
    """

    args = parser.parse_args()

    if args.p:
        try:
            fileHandle = open(args.p)
            fileHandle.close()
        except IOError as errorDef:
            print(errorDef)
        else:
            path = args.p

            return path
    else:
        print(
            "Please specify a path, with -p, to the data file for minstrel-py to run!"
        )
        sys.exit(1)


def get_rc_alg_arg(parser):
    """
    Parses duration argument provided in the exec command
    """

    args = parser.parse_args()

    if args.ralg:
        rc_alg = args.ralg
    else:
        rc_alg = 'minstrel_ht_kernel_space'
    
    return rc_alg

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rateman")
    parser.add_argument("-p", help="Path to the access point list file.", type=str)
    parser.add_argument("-ralg", help="Rate Control Algorithm", type=str)

    args = parser.parse_args()

    if args.p is None:
        print(
            "\nThis rateman script needs path argument to run. Please see the help below!\n"
        )
        parser.print_help()
        sys.exit(1)

    ap_list_path = get_path_arg(parser)
    rate_control_alg = get_rc_alg_arg(parser)
    data_path = "/Users/prashiddhadhojthapa/Desktop/SupraCoNeX/scnx-rateman/demo/data"

    rateMan = rateman.RateMan(ap_list_path, rate_control_alg, data_path)

    start_time = time.time()

    loop = asyncio.get_event_loop()

    try:
       loop.run_forever()
    except (OSError, KeyboardInterrupt) as e:
       time_elapsed = time.time() - start_time
       logging.info("Measurement Completed! Time duration: %f", time_elapsed)
    finally:
       rateMan.stop()
       rateMan.stop_loop()
       loop.close()
       print("Terminated Rateman!")