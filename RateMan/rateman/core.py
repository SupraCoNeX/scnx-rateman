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
import os
import logging


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
    "stop_rateman",
    "check_APs_connection",
    "reconnect_to_AP",
    "restart_radios"
]


async def main_AP_tasks(APInfo, loop, duration=10, output_dir=''):
    """
    This async function creates a main task that manages several
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APInfo : dictionary
        contains parameters such as ID, IP Address and Port with each
        AP as key
    duration : float
        time duration until which data has to be collected

    Returns
    -------
    None.

    """

    APInfo = await connect_to_AP(APInfo, loop, output_dir)

    Active_AP = await check_APs_connection(APInfo, loop)

    # If we have accesible AP/s
    if Active_AP:

        # Start fetching TX and RC status for accessible APs
        init_data_parsing(APInfo)

        loop.create_task(timer(APInfo, duration, loop))

        monitoring_tasks(APInfo, loop)

        # loop.create_task(obtain_data(APInfo))

        # loop.create_task(set_rate(APInfo))

        loop.create_task(stop_trigger(APInfo, loop))

    else:

        logging.error("Couldn't connect to any access points!")
        await stop_rateman(APInfo, loop, stop_cmd=False)


async def connect_to_AP(APInfo: dict, loop, output_dir):
    """
    This async function takes a dictionary of AP information and
    returns the dictionary with only accessible AP entries.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    APInfo : dictionary
        contains parameters such as ID, IP Address and Port with each
        AP as key

    Returns
    -------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key

    """

    APIDs = list(APInfo.keys())

    logging.info("Connecting to access points.")

    if len(output_dir) == 0:
        os.mkdir('data')
        output_dir = os.path.join(os.getcwd(), 'data')

    for APID in APIDs:

        fileHandle = open(output_dir+"/data_" + APID + ".csv", "w")

        conn = asyncio.open_connection(
            APInfo[APID]["IPADD"], APInfo[APID]["MPORT"])

        try:
            # Try connecting to the AP within a timeout duration
            reader, writer = await asyncio.wait_for(conn, timeout=5)
            logging.info(
                "Connected to {} : {} {}".format(
                    APID, APInfo[APID]["IPADD"], APInfo[APID]["MPORT"])
            )

            APInfo[APID]["writer"] = writer
            APInfo[APID]["reader"] = reader
            APInfo[APID]["fileHandle"] = fileHandle

            # Set active connection to True
            APInfo[APID]["conn"] = True

        except (asyncio.TimeoutError, ConnectionError) as e:
            # Incase of a connection error or if the timeout duration is exceeded
            logging.error(
                "Failed to connect {} : {} {} -> {}".format(
                    APID, APInfo[APID]["IPADD"], APInfo[APID]["MPORT"], e
                )
            )
            fileHandle.write(
                "Failed to connect {} {}: {}".format(
                    APInfo[APID]["IPADD"], APInfo[APID]["MPORT"], e
                )
            )

            # Set active connection to False
            APInfo[APID]["conn"] = False

    return APInfo


async def check_APs_connection(APInfo: dict, loop):
    """
    This async function checks if rateman has successfully connected to 
    atleast one AP in APInfo. If not, then rateman returns False which
    indicates that rateman is to be terminated.

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.

    Returns
    -------
    True: If there is atleast one active connection in APInfo
    False: If none of the APs were connected

    """

    APIDs = list(APInfo.keys())

    for APID in APIDs:
        if APInfo[APID]["conn"] is True:
            return True
    
    return False


def init_data_parsing(APInfo: dict) -> None:
    """
    This function, for each phy, executes the command to display the TX and rc 
    status.

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key

    Returns
    -------
    None.

    """

    APIDs = list(APInfo.keys())

    logging.info("Starting radios.")

    cmd_footer = ";start;stats;txs"

    for APID in APIDs:
        if APInfo[APID]["conn"] is True:
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
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    duration: float
        duration after which rateman is to be terminated

    Returns
    -------
    None.

    """
    start_time = time.time()
    while True:
        await asyncio.sleep(0)
        time_elapsed = time.time() - start_time
        if time_elapsed > duration:
            logging.info("Given duration has been exceeded! Time duration: %f", time_elapsed)
            break
    await stop_rateman(APInfo, loop)


def monitoring_tasks(APInfo, loop):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.

    Returns
    -------
    None.

    """

    APIDs = list(APInfo.keys())

    logging.info("Initiating monitoring.")

    for APID in APIDs:
        if APInfo[APID]["conn"] is True:
            loop.create_task(recv_data(APInfo[APID]))


async def recv_data(APInfo):
    """
    This async function for an AP reads the TX and rc status and writes
    it to the data_AP.csv file

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP

    Returns
    -------
    None.

    """
    while True:
        try:
            reader = APInfo['reader']
            fileHandle = APInfo['fileHandle']
            timeout = 600

            # await asyncio.sleep(0.01)
            dataLine = await asyncio.wait_for(reader.readline(), timeout)

            # If rateman reads empty string from reader stream
            if not len(dataLine):
                logging.error("Disconnected from {}".format(APInfo['APID']))
                APInfo['reader'], APInfo['writer'] = await reconnect_to_AP(APInfo)
                await restart_radios(APInfo)
            else:
                fileHandle.write(dataLine.decode("utf-8"))

        except KeyboardInterrupt:
            pass

        except (ConnectionError, asyncio.TimeoutError):
            logging.error("Disconnected from {}".format(APInfo['APID']))
            APInfo['reader'], APInfo['writer'] = await reconnect_to_AP(APInfo)
            await restart_radios(APInfo)
            continue


async def reconnect_to_AP(APInfo):
    """
    This async function reconnects to the given IP Address and Port of
    an APID.

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP

    Returns
    -------
    reader : reader object
        object from which the TX and rc status of an AP is read
    writer : writer object
        object used to execute commands to the rate control API 
        of an AP
    """

    while True:
        recon_delay = 10

        logging.info("Reconnecting to {} in {} seconds. ".format(APInfo['APID'], recon_delay))

        await asyncio.sleep(recon_delay)

        conn = asyncio.open_connection(APInfo['IPADD'], APInfo['MPORT'])

        try:
            # Try connecting to the AP within a timeout duration
            reader, writer = await asyncio.wait_for(conn, timeout=5)
            logging.info("Reconnected to {} : {} {}".format(APInfo['APID'], APInfo['IPADD'], APInfo['MPORT']))
            APInfo['conn'] = True
            return reader, writer

        except (asyncio.TimeoutError, ConnectionError) as e:
            # If timeout duration is exceeded i.e. AP is not accessible
            logging.error("Failed to reconnect {} : {} {} -> {}".format(APInfo['APID'], APInfo['IPADD'], APInfo['MPORT'], e))
            APInfo['conn'] = False
            continue


async def restart_radios(APInfo):
    """
    This async function for an AP restarts the radios i.e. executes the command
    to enable rate control API.

    Parameters
    ----------
    APInfo : dictionary
        ccontains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP

    Returns
    -------
    None.

    """

    cmd_footer = ";start;stats;txs"
    writer = APInfo["writer"]
    
    for phy in APInfo["phyList"]:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")
    
    logging.info("{} : Radios restarted!".format(APInfo['APID']))


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
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.

    Returns
    -------
    None.

    """
    prompt = "To stop RateMan, enter x: \n"
    timeout = 1
    allowedKeys = ["x"]
    try:
        while True:
            await asyncio.sleep(2)
            # answer = timedInput(prompt, timeout)
            answer = timedInputKey(prompt, timeout, allowedKeys)

            if answer == "x":
                await stop_rateman(APInfo, loop)
                break

    except KeyboardInterrupt:
        pass


async def stop_rateman(APInfo, loop, stop_cmd: bool = True):
    """
    This async function executes stop command in the APs (if indicated i.e.
    stop_cmd set to True). It also stops all the tasks and, finally, the
    event loop.

    Parameters
    ----------
    APInfo : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.
    stop_cmd : bool
        if True, it indicates that stop command for TX and rc status must
        be executed before stopping the program

    Returns
    -------
    None.

    """
    cmd_footer = ";stop"

    APIDs = list(APInfo.keys())

    if stop_cmd is True:
        for APID in APIDs:
            if APInfo[APID]["conn"] is True:
                writer = APInfo[APID]["writer"]
                for phy in APInfo[APID]["phyList"]:
                    cmd = phy + cmd_footer
                    writer.write(cmd.encode("ascii") + b"\n")

    logging.info("Stopping rateman.....")
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
