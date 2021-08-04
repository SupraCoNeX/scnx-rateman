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
import datetime

# logging.info("Start: %s", datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"))

__all__ = [
    "setup_rateman_tasks",
    "setup_outputdir",
    "connect_AP",
    "check_net_conn",
    "meas_timer",
    "setup_monitoring_tasks",
    "recv_data",
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

    Returns
    -------
    None.

    """
    output_dir = setup_outputdir(output_dir)

    APIDs = list(net_info.keys())

    for APID in APIDs:
        ap_info = net_info[APID]

        ap_info = connect_AP(APID, ap_info, loop, output_dir)

        if ap_info["conn"] is True:
            start_radios(ap_info)

        net_info[APID] = ap_info

    net_active = await check_net_conn(net_info, loop)

    # If we have accesible AP/s
    if net_active:
        # Start fetching TX and RC status for accessible APs
        loop.create_task(meas_timer(net_info, duration, loop))

        setup_monitoring_tasks(net_info, loop)

        # loop.create_task(obtain_data(net_info))

        # loop.create_task(set_rate(net_info))
    else:
        logging.error(
            datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
            ":",
            "Couldn't connect to any access points!",
        )
        await stop_rateman(net_info, loop, stop_cmd=False)


def setup_outputdir(output_dir):

    if len(output_dir) == 0:
        os.mkdir("data")
        output_dir = os.path.join(os.getcwd(), "data")


async def connect_AP(APID, ap_info: dict, loop, output_dir):

    if "fileHandle" not in ap_info:
        fileHandle = open(output_dir + "/data_" + APID + ".csv", "w")
        ap_info["fileHandle"] = fileHandle

    conn = asyncio.open_connection(ap_info["IPADD"], ap_info["MPORT"])

    try:
        # Try connecting to the AP within a timeout duration
        reader, writer = await asyncio.wait_for(conn, timeout=5)

        logging.info(
            datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
            ":",
            "Connected to {} : {} {}".format(APID, ap_info["IPADD"], ap_info["MPORT"]),
        )

        ap_info["writer"] = writer
        ap_info["reader"] = reader
        ap_info["conn"] = True

    except (asyncio.TimeoutError, ConnectionError) as e:
        # Incase of a connection error or if the timeout duration is exceeded
        logging.error(
            datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
            ":",
            "Failed to connect {} : {} {} -> {}".format(
                APID, ap_info["IPADD"], ap_info["MPORT"], e
            ),
        )
        # fileHandle.write(datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"), ':',
        #     "Failed to connect {} {}: {}".format(ap_info["IPADD"], ap_info["MPORT"], e)
        # )

        # Set active connection to False
        ap_info["conn"] = False

    return ap_info


async def check_net_conn(net_info: dict, loop):
    """
    This async function check if any of the AP in net_info has been sucessfully
    connected. If not then rateman terminates.

    Parameters
    ----------
    net_info : dictionary
        contains each AP in the network as key with relevant parameters
    loop : event_loop
        DESCRIPTION.

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
    net_info : dictionary
        ccontains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP

    Returns
    -------
    None.

    """
    cmd_footer = ";start;stats;txs"
    writer = ap_info["writer"]

    for phy in ap_info["phyList"]:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")

    # logging.info("{} : Radios restarted!".format(ap_info["APID"]))


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

    logging.info(
        datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"), ":", "RateMan started"
    )
    while True:
        await asyncio.sleep(0)
        time_elapsed = time.time() - start_time
        if time_elapsed > duration:
            logging.info(
                datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
                ":",
                "Given duration has been exceeded! Time duration: %f",
                time_elapsed,
            )
            break
    await stop_rateman(net_info, loop)


def setup_monitoring_tasks(net_info, loop):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    net_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status with each AP as key
    loop : event_loop
        DESCRIPTION.

    Returns
    -------
    None.

    """

    APIDs = list(net_info.keys())

    # logging.info("Initiating monitoring.")

    for APID in APIDs:
        if net_info[APID]["conn"] is True:
            loop.create_task(recv_data(net_info[APID]))


async def recv_data(ap_info, reconn_time=600):
    """
    This async function for an AP reads the TX and rc status and writes
    it to the data_AP.csv file

    Parameters
    ----------
    ap_info : dictionary
        contains parameters such as ID, IP Address, Port, relevant file
        streams and connection status of an AP
    time_recon : int
        time duration after which reconnected to a currently inactive AP is
        done.

    Returns
    -------
    None.

    """
    while True:
        try:
            reader = ap_info["reader"]
            fileHandle = ap_info["fileHandle"]

            # await asyncio.sleep(0.01)
            dataLine = await asyncio.wait_for(reader.readline(), reconn_time)

            # If rateman reads empty string from reader stream
            if not len(dataLine):
                logging.error(
                    datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
                    ":",
                    "Disconnected from {}".format(ap_info["APID"]),
                )
                ap_info = await connect_AP(ap_info)
                start_radios(ap_info)
            else:
                fileHandle.write(dataLine.decode("utf-8"))

        except KeyboardInterrupt:
            pass

        except (ConnectionError, asyncio.TimeoutError):
            logging.error(
                datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
                ":",
                "Disconnected from {}".format(ap_info["APID"]),
            )
            ap_info = await connect_AP(ap_info)
            start_radios(ap_info)
            continue


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

    logging.info(
        datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
        ":",
        "Stopping rateman.....",
    )

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
