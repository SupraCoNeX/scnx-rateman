# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Core Asynchronous Control
----------------

This is the main processing module that provides functions to asynchronously 
monitor network status and set rates.

"""

import time
import pdb
import io
import asyncio
from .utils import *
import numpy as np
from .connman import *
import random


__all__ = [
    "recv_data",
    "set_rate",
    "stop_trigger",
    "init_data_parsing",
    "monitoring_tasks",
    "obtain_data",
    "stop_loop",
    "main_AP_tasks",
]


async def main_AP_tasks(APInfo, loop, duration = 10):
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

    for APID in APIDs:

        fileHandle = open("collected_data/data_" + APID + ".csv", "w")
        print("Data file created for", APID)

        reader, writer = await asyncio.open_connection(
            APInfo[APID]["IPADD"], APInfo[APID]["PORT"]
        )

        APInfo[APID]["writer"] = writer
        APInfo[APID]["reader"] = reader
        APInfo[APID]["fileHandle"] = fileHandle

    init_data_parsing(APInfo)
    
    
    start_time = time.time()

    monitoring_tasks(APInfo, loop)

    # loop.create_task(obtain_data(APInfo))
    
    # loop.create_task(set_rate(APInfo))

    loop.create_task(stop_trigger(APInfo, loop, duration, start_time))
    

def init_data_parsing(APInfo: dict) -> None:

    """
    This function, for each phy, starts to display the TX and rc status.

    Parameters
    ----------
    APs : list of pairs of IPADDR and Port for each AP in the network
        DESCRIPTION.

    Returns
    -------
    None.

    """

    APIDs = list(APInfo.keys())

    print("starting radios")

    cmd_footer = ";start;stats;txs"

    for APID in APIDs:
        writer = APInfo[APID]["writer"]
        for phy in APInfo[APID]["phyList"]:
            cmd = phy + cmd_footer
            writer.write(cmd.encode("ascii") + b"\n")

    pass


def monitoring_tasks(APInfo, loop):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    APs : list of pairs of IPADDR and Port for each AP in the network
        DESCRIPTION.

    Returns
    -------
    None.

    """

    APIDs = list(APInfo.keys())

    for APID in APIDs:
        loop.create_task(
            recv_data(APInfo[APID]["reader"], APInfo[APID]["fileHandle"]))


async def recv_data(reader, fileHandle):
    """
    This function, for each AP, reads the TX and rc status and writes it to the data_AP.csv file

    Parameters
    ----------
    APs : list of pairs of IPADDR and Port for each AP in the network
        DESCRIPTION.

    Returns
    -------
    None.

    """
    try:
        while True:
            # await asyncio.sleep(0.01)
            dataLine = await reader.readline()
            print("parsing data")
            fileHandle.write(dataLine.decode("utf-8"))
    except KeyboardInterrupt:
        pass
    reader.close()

async def obtain_data(fileHandle) -> None:
    pass

async def set_rate(APInfo) -> None:

    try:
        print("in rate setter")

        APID = "AP2"
        phy = "phy1"
        macaddr = APInfo[APID]["staList"]["wlan1"][0]
        writer = APInfo[APID]["writer"]

        def cmd(phy, macaddr, rate):
            return phy + ";rates;" + macaddr + ";" + rate + ";1"

        while True:
            await asyncio.sleep(0.05)

            APInfo = getStationList(APInfo)
            print("setting rate now")
            writer.write((phy + ";manual").encode("ascii") + b"\n")
            rate_ind = str(random.Random().randint(80, 87))

            writer.write(cmd(phy, macaddr, rate_ind).encode("ascii") + b"\n")
            writer.write((phy + ";auto").encode("ascii") + b"\n")
    except KeyboardInterrupt:
        pass
    writer.close()

async def stop_trigger(APInfo, loop, duration, start_time):
    """
    This function stops the program (data collection) according to the given duration or timedInput.

    Parameters
    ----------
    APs : list of pairs of IPADDR and Port for each AP in the network
        DESCRIPTION.
    loop : event_loop
        DESCRIPTION.
    duration : int
        duration for which the data has to be collected
    start_time : time
        Local time at which the data collection was started

    Returns
    -------
    None.

    """
    timeout = 1
    prompt = "To stop RateMan, enter x.\n"
    cmd_footer = ";stop"

    APIDs = list(APInfo.keys())

    try:
        while True:
            await asyncio.sleep(2)
            answer = timedInput(prompt, timeout)
            
            print('time passed %f seconds' %(time.time()-start_time))

            if answer == "x" or (time.time()-start_time >= duration):
                print("RateMan will stop now.")

                for APID in APIDs:
                    writer = APInfo[APID]["writer"]
                    for phy in APInfo[APID]["phyList"]:
                        cmd = phy + cmd_footer
                        writer.write(cmd.encode("ascii") + b"\n")

                await stop_tasks()
                break

    except KeyboardInterrupt:
        pass

    finally:
        stop_loop(loop)


async def stop_tasks():

    for task in asyncio.all_tasks():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def stop_loop(loop):

    for task in asyncio.all_tasks():
        task.cancel()

    loop.stop()
