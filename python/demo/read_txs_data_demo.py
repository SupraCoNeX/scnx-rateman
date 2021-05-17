# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Demo for reading TX status data 
----------------

This demo script illustrates the basic use of the RateManager package to 
parse TX status data from multiple APs into designated .csv files. 

"""

import ratemanager
import time
import paramiko


if __name__ == "__main__":
    

    # # Create rateman object
    rateMan = ratemanager.RateManager()
    
    rateMan.addaccesspoints('ap_list_sample.csv') 
    
    rateMan.start_monitoring()
    
    time.sleep(10)
    
    rateMan.stop()
    
    
