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

if __name__ == "__main__":
    
    ### pre-requisites

    # Default values for path and duration
    path = "sample_ap_lists/ap_list_sample_1.csv"
    duration = 5

    # Parser to set file path (-p) and time duration (-t)
    parser = argparse.ArgumentParser(description="Rateman")
    parser.add_argument("-p", help="Path to the Access Point File",
                        type = str)
    parser.add_argument("-t", help="Time duration in seconds",
                        type = float)
    
    args = parser.parse_args()

    if args.p is None or args.t is None:
        print("\nThis rateman scripts needs both time and path arguments to run. Please see the help below!\n")
        parser.print_help()


    if args.p:
        try:
            f = open(args.p)
            f.close()
        except IOError as e:
            print(e)
        else:
            path = args.p

    if args.t:
        if args.t > 0:
            duration = args.t
        else:
            print("Oops! Time duration cannot be negative.")


    # # Create rateman object
    rateMan = rateman.RateMan()

    rateMan.addaccesspoints(path)

    rateMan.start(duration)
    
    
    ### clean-up
   
 