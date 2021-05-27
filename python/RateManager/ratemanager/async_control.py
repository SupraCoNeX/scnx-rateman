# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Asynchronous Control
----------------

This module provides functions to asynchronous monitor network status and 
set rates.

"""

import time
import pdb
import io
import asyncio
from .utils import *
import numpy as np
from .connection import *


__all__ = ["recv_data", "set_rate", "stop_trigger", "setup_AP_tasks", "main_AP_tasks"]



async def main_AP_tasks(APInfo, loop):
    """
    This async function creates a main task that manages several 
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APs : list of pairs of IPADDR and Port for each AP in the network
        DESCRIPTION.

    Returns
    -------
    None.

    """

    APIDs = list(APInfo.keys())
    
    task_list = []

    for APID in APIDs:
        
        fileHandle = open("collected_data/data_" + APID + ".csv", "w")
        print("Data file created for", APID)
                
        task_item = setup_AP_tasks(APInfo[APID]['IPADD'],
                                        APInfo[APID]['PORT'], fileHandle, loop)
        loop.create_task(task_item)
        
    
    loop.create_task(stop_trigger(loop))


async def setup_AP_tasks(IPADD, Port, fileHandle, loop):
    
    reader, writer = await asyncio.open_connection(IPADD, Port)
    APHandle = open_connection(IPADD, Port)
    
    print('starting radio')
    cmd = "phy1;start;stats;txs"
    
    writer.write(cmd.encode("ascii") + b"\n")

    # APHandle.send(cmd.encode("ascii") + b"\n")
    
    loop.create_task(recv_data(reader, fileHandle))
    loop.create_task(set_rate(APHandle))    


async def recv_data(reader, fileHandle):
    try:
        while True:
            dataLine = await reader.readline()
            print('parsing data')
            fileHandle.write(dataLine.decode("utf-8"))
    except KeyboardInterrupt:   
        pass
    reader.close()
    
async def set_rate(writer):
    try:
        while True:
            await asyncio.sleep(5)
            rate_ind = np.random.randint(0, 15)
            print("setting rate")
            # writer.write(("phy1;setr;rate_1:mcs"+str(rate_ind)).encode())
            # await writer.drain()
    except KeyboardInterrupt:
        pass
    writer.close()

async def stop_trigger(loop):
    timeout = 1
    prompt = 'To stop RateMan, enter stop.\n'
    try:
        while True:
            await asyncio.sleep(2)
            answer = timedInput(prompt, timeout)
            # print('Doing: ', answer)
            if answer == 'stop':
                print('RateMan will stop now.')
                # reader.close()
                # writer.close()
                # fileHandle.close()
                for task in asyncio.all_tasks():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        print("task is cancelled now")
                loop.stop()
                # loop.close()
                
    except KeyboardInterrupt:
        pass
    loop.stop()
    





    