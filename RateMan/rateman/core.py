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

import numpy as np
from .connman import connect_AP, _check_net_conn
import random
import os
import logging

__all__ = [
    "setup_rateman_tasks",
    "setup_data_dir",
    "start_radios",
    "meas_timer",
    "setup_monitoring_tasks",
    "handle_initial_disconnect",
    "handle_ap_disconn",
    "recv_data",
    "detect_txs_lines",
    "detect_sta_lines",
    "detect_group_header",
    "remove_headers",
    "set_rate",
    "stop_rateman",
    "stop_tasks",
    "stop_loop",
]


async def setup_rateman_tasks(rateMan: object, duration=10, output_dir=""):
    """
    This async function creates a main task that manages several
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    rateMan: object
        Instance of RateMan class which consists of accesspoint information
        for initial connection
    duration : float
        time duration until which data has to be collected
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    output_dir = setup_data_dir(output_dir)

    net_info = rateMan.accesspoints

    APIDs = list(net_info.keys())

    for APID in APIDs:
        await connect_AP(APID, rateMan, output_dir)

        if rateMan.get_conn(APID) is True:
            start_radios(APID, rateMan)

    net_active = await _check_net_conn(rateMan)

    if net_active:

        rateMan.loop.create_task(meas_timer(rateMan, duration))

        setup_monitoring_tasks(rateMan, output_dir)

    else:
        logging.error("Couldn't connect to any access points!")
        await stop_rateman(rateMan, stop_cmd=False)


def setup_data_dir(output_dir):

    if len(output_dir) == 0:
        if not os.path.exists("data"):
            os.mkdir("data")
        output_dir = os.path.join(os.getcwd(), "data")

    return output_dir


def start_radios(APID, rateMan: object):
    """
    This async function for an AP starts the radios i.e. executes the command
    to enable rate control API.

    Parameters
    ----------
    APID: str
        ID of the Access Point
    rateMan: object
        Instance of RateMan class

    Returns
    -------
    None.

    """

    net_info = rateMan.accesspoints
    writer = net_info[APID]["writer"]
    phy_list = net_info[APID]["phyList"]

    cmd_footer = ";stop"
    for phy in phy_list:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")

    cmd_footer = ";dump"
    for phy in phy_list:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")

    cmd_footer = ";start;stats;txs"
    for phy in phy_list:
        cmd = phy + cmd_footer
        writer.write(cmd.encode("ascii") + b"\n")


async def meas_timer(rateMan: object, duration):
    """
    This async function stops the rateman after the TX and rc data have
    been parsed for a time duration.

    Parameters
    ----------
    rateMan: object
        Instance of RateMan class
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
    await stop_rateman(rateMan)


def setup_monitoring_tasks(rateMan: object, output_dir):
    """
    This function, for each AP, calls the recv_data function.

    Parameters
    ----------
    rateMan: object
        Instance of RateMan class
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    net_info = rateMan.accesspoints
    APIDs = list(net_info.keys())

    for APID in APIDs:
        if net_info[APID]["conn"] is True:
            rateMan.loop.create_task(recv_data(APID, rateMan, output_dir))
        else:
            rateMan.loop.create_task(
                handle_initial_disconnect(APID, rateMan, output_dir)
            )


async def handle_initial_disconnect(APID: str, rateMan: object, output_dir):
    """
    This async function retries connecting to APs that weren't succesfully
    connected during the first attempt.

    Parameters
    ----------
    APID: str
        ID of the Access Point
    rateMan: object
        Instance of RateMan class
    output_dir : str
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    await handle_ap_disconn(APID, rateMan, output_dir, prev_conn=False)
    await recv_data(APID, rateMan, output_dir)


async def handle_ap_disconn(
    APID: str, rateMan: object, output_dir, prev_conn, reconn_delay=20
):
    """
    This async function handles disconnect from AP and skips headers when
    reading from the ReaderStream again.

    Parameters
    ----------
    APID : str
        ID of the Access Point
    rateMan: object
        Instance of RateMan class
    output_dir : str
        the main directory where results of the experiment are stored
    prev_conn: bool
        specifies whether the connection has been established before. This
        determines whether to remove headers or not
    reconn_delay: int
        time delay between consecutive reconnection attempts

    Returns
    -------
    None.

    """

    if prev_conn is True:
        logging.error("Disconnected from {}".format(APID))
    else:
        logging.error("Couldn't establish initial connection to {}".format(APID))

    rateMan.set_conn(APID, False)

    while rateMan.get_conn(APID) is not True:
        await asyncio.sleep(reconn_delay)
        await connect_AP(APID, rateMan, output_dir)

    start_radios(APID, rateMan)

    if prev_conn is True:
        await remove_headers(APID, rateMan, output_dir)


async def recv_data(APID: str, rateMan: object, output_dir, reconn_time=600):
    """
    This async function for an AP reads the TX and rc status and writes
    it to the data_AP.csv file

    Parameters
    ----------
    APID: str
        ID of the Access Point
    rateMan: object
        Instance of RateMan class
    output_dir : str
        the main directory where results of the experiment are stored
    reconn_time : int
        timeout duration for readline after which reconnection to an AP
        is attempted.

    Returns
    -------
    None.

    """
    while True:
        try:
            net_info = rateMan.accesspoints
            ap_info = net_info[APID]

            reader = ap_info["reader"]
            fileHandle = ap_info["fileHandle"]

            dataLine = await asyncio.wait_for(reader.readline(), reconn_time)
            dataLine = dataLine.decode("utf-8")

            detect_group_header(APID, rateMan, dataLine)
            detect_sta_lines(APID, rateMan, dataLine)
            detect_txs_lines(APID, rateMan, dataLine)

            # Reading empty string means rateman is no longer connected to AP
            if not len(dataLine):
                await handle_ap_disconn(APID, rateMan, output_dir, prev_conn=True)
            else:
                fileHandle.write(dataLine)

        except KeyboardInterrupt:
            pass

        except (ConnectionError, asyncio.TimeoutError):
            await handle_ap_disconn(APID, rateMan, output_dir, prev_conn=True)
            continue


def detect_txs_lines(APID: str, rateMan: object, dataLine):
    """
    This function updates the stats (success and attempts) for rates listed in the txs
    lines.

    Parameters
    ----------
    APID : str
        ID of the Access Point associated with the txs_line
    rateMan : object
        Instance of RateMan class
    dataLine:
        data line recevied from the AP

    Returns
    -------
    None.

    """

    txs_line = dataLine.strip("\n").split(";")
    if txs_line[2] != "txs":
        return

    client_MAC = txs_line[3]
    data_frames_dec = int(txs_line[4], 16)

    # Current implementation requires rate-count info to start from 8th position
    rate_count_raw = txs_line[7:]
    rate = rate_count_raw[0::2]
    count = rate_count_raw[1::2]
    rate_count = list(zip(rate, count))

    try:
        while True:
            rate_count.remove(("ffff", "0"))
    except ValueError:
        pass

    len_rates = len(rate_count)

    for i, rate_attempt in enumerate(rate_count):
        rate, count = rate_attempt
        if len(rate) == 1:
            rate = "0" + rate

        supp_rates = rateMan.get_suppRates_client(APID, client_MAC)

        if not supp_rates:
            return

        if rate in supp_rates:

            count_dec = int(count, 16)

            attempts = supp_rates[rate]["attempts"] + (count_dec * data_frames_dec)
            rateMan.update_attempts(APID, client_MAC, rate, attempts)

            # If it is the last rate_count pair, thenit was successful
            if i + 1 == len_rates:
                num_ack_frame = txs_line[5]
                success = supp_rates[rate]["success"] + int(num_ack_frame, 16)
                rateMan.update_success(APID, client_MAC, rate, success)

        else:
            logging.info(
                "TXS line with unsupported rate for",
                APID,
                "! MAC ADD:",
                client_MAC,
                " Used Rate:",
                rate,
            )


def detect_sta_lines(APID: str, rateMan: object, dataLine):
    """
    This function detects the sta (station) lines sent from AP and makes
    changes on the clients data structure depending on action

    Parameters
    ----------
    APID : str
        ID of the Access Point associated with the sta_line
    rateMan : object
        Instance of RateMan class
    dataLine:
        data line recevied from the AP

    Returns
    -------
    None.

    """

    param = dataLine.split(";")

    if len(param) > 5 and param[2] == "sta":
        MAC_Add = param[4]

        if param[3] == "add" or param[3] == "dump":
            phy = param[0]
            rates_flag = param[7:]
            supp_groupIdx = []

            for i, (groupIdx, max_offset) in enumerate(
                rateMan.get_suppRates_AP(APID).items()
            ):
                # Still need to implement for other masks
                if rates_flag[i] == "ff":
                    offset = groupIdx + "0"
                    no_rates = int(max_offset[-1]) + 1

                    supp_groupIdx += [offset[:-1] + str(i) for i in range(no_rates)]

            if supp_groupIdx:
                rateMan.add_station(APID, MAC_Add, supp_groupIdx, phy)

        if param[3] == "remove":
            # rateMan.remove_station(APID, MAC_Add)
            pass


def detect_group_header(APID: str, rateMan: object, dataLine):
    """
    This function detects group header lines which indicate the
    supported rates of the access points (APID)

    Parameters
    ----------
    APID : str
        ID of the Access Point
    rateMan : object
        Instance of RateMan class
    dataLine:
        data line recevied from the AP

    Returns
    -------
    None.

    """
    pattern = "*;0;group;"

    if pattern in dataLine:
        param = dataLine.strip("\n").split(";")
        param = list(filter(None, param))
        groupIdx = param[3]
        offset = param[4]

        max_offset = offset[:-1] + str(len(param[9:]) - 1)
        rateMan.add_suppRate_AP(APID, groupIdx, max_offset)


async def remove_headers(APID: str, rateMan: object, output_dir):
    """
    This async function for a reconnected AP skips writing format header
    to the data file again.

    Parameters
    ----------
    APID : str
        ID of the Access Point
    rateMan : object
        Instance of RateMan class
    output_dir:
        the main directory where results of the experiment are stored

    Returns
    -------
    None.

    """
    while True:
        try:
            net_info = rateMan.accesspoints
            ap_info = net_info[APID]

            reader = ap_info["reader"]
            fileHandle = ap_info["fileHandle"]

            dataLine = await asyncio.wait_for(reader.readline(), timeout=10)

            # Reading empty string means rateman is no longer connected to AP
            if not len(dataLine):
                handle_ap_disconn(APID, rateMan, output_dir, prev_conn=True)
                break
            else:
                # terminate while loop when it encounters a non header line
                line = dataLine.decode("utf-8")
                if line[0] != "*":
                    fileHandle.write(line)
                    break

        except (ConnectionError, asyncio.TimeoutError):
            handle_ap_disconn(APID, rateMan, output_dir, prev_conn=True)
            break


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


async def stop_rateman(rateMan: object, stop_cmd: bool = True):
    """
    This async function executes stop command in the APs (if indicated i.e.
    stop_cmd set to True). It also stops all the tasks and, finally, the
    event loop.

    Parameters
    ----------
    rateMan : object
        Instance of RateMan class
    stop_cmd : bool
        if True, it indicates that stop command for TX and rc status must
        be executed before stopping the program

    Returns
    -------
    None.

    """
    cmd_footer = ";stop"

    net_info = rateMan.accesspoints
    APIDs = list(net_info.keys())

    if stop_cmd is True:
        for APID in APIDs:
            ap_info = net_info[APID]
            if ap_info["conn"] is True:
                writer = ap_info["writer"]
                for phy in ap_info["phyList"]:
                    cmd = phy + cmd_footer
                    writer.write(cmd.encode("ascii") + b"\n")

    logging.info("Stopping rateman.....")

    await stop_tasks()
    stop_loop(rateMan.loop)


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
