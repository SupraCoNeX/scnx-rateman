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
    
    ### pre-requisites

    # Parser to set file path (-p) and time duration (-t)
    parser = argparse.ArgumentParser(description="Rateman")
    parser.add_argument("-p", help="Path to the Access Point File",
                        type = str)
    parser.add_argument("-t", help="Time duration in seconds",
                        type = float)
    
    args = parser.parse_args()

    #If one of the arguments, from -p and -t, is missing then print_help() and terminate
    if args.p is None or args.t is None:
        print("\nThis rateman script needs both time and path arguments to run. Please see the help below!\n")
        parser.print_help()
        sys.exit(1)

    # Store path of the AP file
    if args.p:
        try:
            f = open(args.p)
            f.close()
        except IOError as e:
            print(e)
            sys.exit(2)
        else:
            path = args.p

    # Store the duration of the experiment
    if args.t:
        if args.t > 0:
            duration = args.t
        else:
            print("Oops! Time duration cannot be negative.")
            sys.exit(3)


    # # Create rateman object
    rateMan = rateman.RateMan()

    rateMan.addaccesspoints(path)

    rateMan.start(duration)
    
    ### clean-up
   
 