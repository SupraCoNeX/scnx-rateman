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
import asyncio
from .utils import *
import numpy as np
from .connman import *
import random
import os
import logging

__all__ = [
    "setup_rateman_tasks",
    "setup_outputdir",
    "connect_AP",
    "check_net_conn",
    "start_radios",
    "meas_timer",
    "setup_monitoring_tasks",
    "handle_initial_disconnect",
    "recv_data",
    "handle_disconnects",
    "remove_headers",
    "obtain_data",
    "set_rate",
    "stop_rateman",
    "stop_tasks",
    "stop_loop",
]


async def setup_rateman_tasks(net_info, loop, duration=10, output_dir=""):
    """
    This async function creates a main task that manages several
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    net_info : dictionary
        contains keys denote AP names, which are itself dictionaries
        each containing parameters including; AP ID, IP Address,
        SSHPort, and Minstrel Port.
    duration : float
        time duration until which data has to be collected
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    output_dir = setup_outputdir(output_dir)

    APIDs = list(net_info.keys())

    for APID in APIDs:
        ap_info = net_info[APID]

        ap_info = await connect_AP(ap_info, output_dir)

        if ap_info["conn"] is True:
            start_radios(ap_info)

        net_info[APID] = ap_info

    net_active = await check_net_conn(net_info)

    if net_active:

        loop.create_task(meas_timer(net_info, duration, loop))

        setup_monitoring_tasks(net_info, loop, output_dir)

    else:
        logging.error("Couldn't connect to any access points!")
        await stop_rateman(net_info, loop, stop_cmd=False)


def setup_outputdir(output_dir):

    if len(output_dir) == 0:
        os.mkdir("data")
        output_dir = os.path.join(os.getcwd(), "data")

    return output_dir


async def connect_AP(ap_info: dict, output_dir):
    """
    This async function takes a dictionary containing information about
    an AP and connects with it.

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address and Port of an AP
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    """

    if "fileHandle" not in ap_info:

        fileHandle = open(output_dir + "/data_" + ap_info["APID"] + ".csv", "w")
        ap_info["fileHandle"] = fileHandle

    conn_handle = asyncio.open_connection(ap_info["IPADD"], ap_info["MPORT"])

    try:
        # Try connecting to the AP within a timeout duration
        reader, writer = await asyncio.wait_for(conn_handle, timeout=5)

        logging.info(
            "Connected to {} : {} {}".format(
                ap_info["APID"], ap_info["IPADD"], ap_info["MPORT"]
            )
        )

        ap_info["writer"] = writer
        ap_info["reader"] = reader
        ap_info["conn"] = True

    except (asyncio.TimeoutError, ConnectionError) as e:
        # Incase of a connection error or if the timeout duration is exceeded
        logging.error(
            "Failed to connect {} : {} {} -> {}".format(
                ap_info["APID"], ap_info["IPADD"], ap_info["MPORT"], e
            )
        )

        # Set active connection to False
        ap_info["conn"] = False

    return ap_info


async def check_net_conn(net_info: dict):
    """
    This async function check if any of the AP in net_info has been sucessfully
    connected. If not then rateman terminates.

    Parameters
    ----------
    net_info : dictionary
        contains each AP in the network as key with relevant parameters

    Returns
    -------
    True: If there is atleast one active connection in net_info
    False: If none of the APs were connected

    """
    APIDs = list(net_info.keys())

    for APID in APIDs:
        if net_info[APID]["conn"] is True:
            return True

    return False


def start_radios(ap_info):
    """
    This async function for an AP starts the radios i.e. executes the command
    to enable rate control API.

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP

    Returns
    -------
    None.

    """

    writer = ap_info["writer"]

    cmd_footer = ";stop"
    for phy in ap_info["phyList"]:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")

    cmd_footer = ";start;stats;txs"
    for phy in ap_info["phyList"]:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")


async def meas_timer(net_info, duration, loop):
    """
    This async function stops the rateman after the TX and rc data have
    been parsed for a time duration.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    net_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    duration: float
        duration after which rateman is to be terminated

    Returns
    -------
    None.

    """
    start_time = time.time()

    logging.info("RateMan started")
    while True:
        await asyncio.sleep(0)
        time_elapsed = time.time() - start_time
        if time_elapsed > duration:
            logging.info(
                "Given duration has been exceeded! Time duration: %f", time_elapsed
            )
            break
    await stop_rateman(net_info, loop)


def setup_monitoring_tasks(net_info, loop, output_dir):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    net_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """

    APIDs = list(net_info.keys())

    for APID in APIDs:
        if net_info[APID]["conn"] is True:
            loop.create_task(recv_data(net_info[APID], output_dir))
        else:
            loop.create_task(handle_initial_disconnect(net_info[APID], output_dir))

async def handle_initial_disconnect(ap_info, output_dir):
    """
    This async function retries connecting to APs that weren't succesfully 
    connected during the first attempt. 

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.
    """
    ap_info = await handle_disconnects(ap_info, output_dir, prev_conn=False)
    await recv_data(ap_info, output_dir)


async def recv_data(ap_info, output_dir, reconn_time=600):
    """
    This async function for an AP reads the TX and rc status and writes
    it to the data_AP.csv file

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    output_dir : str
        the main directory where results of the experiment are stored
    reconn_time : int
        duration for readline timeout after which reconnection to a currently 
        inactive AP is attempted.

    Returns
    -------
    None.

    """
    while True:
        try:
            reader = ap_info["reader"]
            fileHandle = ap_info["fileHandle"]

            dataLine = await asyncio.wait_for(reader.readline(), reconn_time)

            # Reading empty string means rateman is no longer connected to AP
            if not len(dataLine):
                ap_info = await handle_disconnects(ap_info, output_dir, prev_conn=True)
            else:
                fileHandle.write(dataLine.decode("utf-8"))

        except KeyboardInterrupt:
            pass

        except (ConnectionError, asyncio.TimeoutError):
            ap_info = await handle_disconnects(ap_info, output_dir, prev_conn=True)
            continue


async def handle_disconnects(ap_info, output_dir, prev_conn, reconn_delay=20):
    """
    This async function handles disconnect from AP and skips headers when
    reading from the ReaderStream again.

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    output_dir : str
        the main directory where results of the experiment are stored
    reconn_delay: int
        time delay between consecutive reconnection attempts
    prev_conn: bool
        specifies whether the connection has been established before or
        not. This determines whether to remove headers or not.

    Returns
    -------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file 
        streams and connection status of an AP
    """

    if prev_conn is True:
        logging.error("Disconnected from {}".format(ap_info["APID"]))
    else:
        logging.error("Couldn't establish initial connection to {}".format(ap_info["APID"]))
    
    ap_info["conn"] = False

    while ap_info["conn"] is not True:
        await asyncio.sleep(reconn_delay)
        ap_info = await connect_AP(ap_info, output_dir)
    
    start_radios(ap_info)

    if prev_conn is True:
        await remove_headers(ap_info, output_dir)

    return ap_info


async def remove_headers(ap_info, output_dir):
    """
    This async function for a reconnected AP skips writing format header
    to the data file again.

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    while True:
        try:
            reader = ap_info["reader"]
            fileHandle = ap_info["fileHandle"]

            dataLine = await asyncio.wait_for(reader.readline(), timeout=10)

            # Reading empty string means rateman is no longer connected to AP
            if not len(dataLine):
                ap_info = handle_disconnects(ap_info, output_dir)
                break
            else:
                # terminate while loop when it encounters a non header line
                line = dataLine.decode("utf-8")
                if line[0] != '*':
                    fileHandle.write(line)
                    break

        except (ConnectionError, asyncio.TimeoutError):
            ap_info = handle_disconnects(ap_info, output_dir)
            break
    
    return ap_info


async def obtain_data(fileHandle) -> None:
    pass


async def set_rate(net_info) -> None:

    try:
        print("in rate setter")

        APID = "AP2"
        phy = "phy1"
        macaddr = net_info[APID]["staList"]["wlan1"][0]
        writer = net_info[APID]["writer"]

        def cmd(phy, macaddr, rate):
            return phy + ";rates;" + macaddr + ";" + rate + ";1"

        while True:
            await asyncio.sleep(0.05)

            net_info = getStationList(net_info)
            print("setting rate now")
            writer.write((phy + ";manual").encode("ascii") + b"\n")
            rate_ind = str(random.Random().randint(80, 87))

            writer.write(cmd(phy, macaddr, rate_ind).encode("ascii") + b"\n")
            writer.write((phy + ";auto").encode("ascii") + b"\n")
    except KeyboardInterrupt:
        pass
    writer.close()


async def stop_rateman(net_info, loop, stop_cmd: bool = True):
    """
    This async function executes stop command in the APs (if indicated i.e.
    stop_cmd set to True). It also stops all the tasks and, finally, the
    event loop.

    Parameters
    ----------
    net_info : dictionary
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

    APIDs = list(net_info.keys())

    if stop_cmd is True:
        for APID in APIDs:
            if net_info[APID]["conn"] is True:
                writer = net_info[APID]["writer"]
                for phy in net_info[APID]["phyList"]:
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
