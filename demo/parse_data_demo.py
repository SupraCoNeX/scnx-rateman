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
import time
import paramiko
import argparse
import sys

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Rateman")
    parser.add_argument("-p", help="Path to the access point list file.", type=str)
    parser.add_argument("-t", help="Measurement time duration in seconds.", type=float)
    parser.add_argument('--notify', help='Enable telegram notification', action='store_true')

    args = parser.parse_args()

    if args.p is None or args.t is None:
        print(
            "\nThis rateman script needs both time and path arguments to run. Please see the help below!\n"
        )
        parser.print_help()
        sys.exit(1)

    path = rateman.get_path_arg(parser)
    
    duration = rateman.get_duration_arg(parser)

    rateMan = rateman.RateMan()

    rateMan.addaccesspoints(path)

    rateMan.start(duration, notify=args.notify)
