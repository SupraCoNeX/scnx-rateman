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

if __name__ == "__main__":

    # # Create rateman object
    
    ### pre-requisites
    
        
    duration = 10 
    
    rateMan = rateman.RateMan()

    rateMan.addaccesspoints("sample_ap_lists/ap_list_sample_1.csv")

    rateMan.start(duration)
    
    
    ### clean-up
   
 