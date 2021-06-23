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
    "connect_to_AP",
    "timer",
    "stop_rateman"
]


async def main_AP_tasks(APInfo, loop, duration = 10):
    """
    This async function creates a main task that manages several
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters
    duration : float
        duration for which the data has to be collected

    Returns
    -------
    None.

    """

    APInfo =  await connect_to_AP(APInfo, loop)
    
    # If we have accesible AP/s
    if APInfo:

        # Start fetching TX and RC status for accessible APs
        init_data_parsing(APInfo)

        loop.create_task(timer(APInfo, duration, loop))

        monitoring_tasks(APInfo, loop)

        # loop.create_task(obtain_data(APInfo))
    
        # loop.create_task(set_rate(APInfo))

        loop.create_task(stop_trigger(APInfo, loop))
    
async def connect_to_AP(APInfo: dict, loop):
    """
    This async function takes a dictionary of AP information and
    returns the dictionary with only accessible AP entries.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters

    Returns
    -------
    APInfo : dictionary
        contains each accessible AP in the network as key with relevant parameters

    """

    APIDs = list(APInfo.keys())

    for APID in APIDs:

        fileHandle = open("collected_data/data_" + APID + ".csv", "w")
        print("Data file created for", APID)

        conn = asyncio.open_connection(
            APInfo[APID]["IPADD"], APInfo[APID]["PORT"]
        )

        try:
            # Try connecting to the AP within a timeout duration
            reader, writer = await asyncio.wait_for(conn, timeout=5)
            print ("Connected to {} {}".format(APInfo[APID]["IPADD"], APInfo[APID]["PORT"]))

            APInfo[APID]["writer"] = writer
            APInfo[APID]["reader"] = reader
            APInfo[APID]["fileHandle"] = fileHandle

        except asyncio.TimeoutError:
            # If timeout duration is exceeded i.e. AP is not accessible
            print ("Failed to connect {} {}: Timeout Error".format(APInfo[APID]["IPADD"], APInfo[APID]["PORT"]))
            fileHandle.write("Failed to connect {} {}: Timeout Error".format(APInfo[APID]["IPADD"], APInfo[APID]["PORT"]))

            # Remove unaccessible AP from the dictionary
            del APInfo[APID]

            # Check if the list of accessible APs is empty
            if not APInfo:
                print("Couldn't connect to any access points! Stopping rateman....")
                await stop_rateman(APInfo, loop, False)
    
    return APInfo

def init_data_parsing(APInfo: dict) -> None:

    """
    This function, for each phy, starts to display the TX and rc status.

    Parameters
    ----------
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters

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

async def timer(APInfo, duration, loop):
    """
    This async function stops the rateman after the TX and rc data have
    been parsed for a time duration.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters
    duration: float
        calls stop_rateman function when the duration is exceeded

    Returns
    -------
    None.

    """
    start_time = time.time()
    while True:
        await asyncio.sleep(0)
        time_elapsed = time.time()-start_time
        if time_elapsed > duration:
            print("Given duration has been exceeded! Time duration: ", time_elapsed)
            break
    await stop_rateman(APInfo, loop)

def monitoring_tasks(APInfo, loop):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters
    loop : event_loop
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
    reader : reader object
        object from which the TX and rc status of an AP is read
    fileHandle : file object
        the data_AP.csv file to which the TX and rc status has to be written

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

async def stop_trigger(APInfo, loop):
    """
    This function calls stop_rateman when the timedInput function
    gets the expected input i.e. x.

    Parameters
    ----------
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters
    loop : event_loop
        DESCRIPTION.

    Returns
    -------
    None.

    """
    timeout = 1
    prompt = "To stop RateMan, enter x.\n"
    
    try:
        while True:
            await asyncio.sleep(2)
            answer = timedInput(prompt, timeout)

            if answer == "x":
                stop_rateman(APInfo, loop)
                break

    except KeyboardInterrupt:
        pass

async def stop_rateman(APInfo, loop, stop_cmd: bool = True):
    """
    This function calls stop_rateman when the timedInput function
    gets the expected input i.e. x.

    Parameters
    ----------
    APInfo : dictionary
        contains each AP in the network as key with relevant parameters
    loop : event_loop
        DESCRIPTION.
    stop_cmd : bool
        if True indicates that stop command for TX and rc status must be 
        executed before stopping the program 

    Returns
    -------
    None.

    """
    cmd_footer = ";stop"

    APIDs = list(APInfo.keys())

    if stop_cmd is True:
        for APID in APIDs:
            writer = APInfo[APID]["writer"]
            for phy in APInfo[APID]["phyList"]:
                cmd = phy + cmd_footer
                writer.write(cmd.encode("ascii") + b"\n")

    print("Stopping rateman.....")
    await stop_tasks()
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
