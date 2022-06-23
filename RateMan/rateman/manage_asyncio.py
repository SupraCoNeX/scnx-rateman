# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Manage Asynchronous I/O Tasks
-----------------------------

This is the main processing module that provides functions to asynchronously 
monitor network status and set rates.

"""

import time
import asyncio
import os
import logging
from . import manage_line
import mexman

__all__ = [
    "setup_ap_tasks",
    "setup_data_dir",
    "collect_data",
    "remove_headers",
    "reconn_ap_list",
]


async def setup_ap_tasks(ap_handles, output_dir=""):
    """
    This async function creates a main task that manages several
    subtasks with each AP having one subtask associated with it.

    Parameters
    ----------
    loop : event_loop
        DESCRIPTION.
    ap_handles : dictionary
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
    loop = asyncio.get_running_loop()
    output_dir = setup_data_dir(output_dir)

    for APID in list(ap_handles.keys()):
        ap_handle = ap_handles[APID]

        await ap_handle.connect_AP(output_dir)

        if ap_handle.connection is True:
            ap_handle.once_connected = True
            ap_handle.start_radios()
        else:
            logging.error(
                "Couldn't establish initial connection to {}".format(ap_handle.AP_ID)
            )

    if _check_net_conn(ap_handles):

        for APID in list(ap_handles.keys()):
            if ap_handles[APID].connection:
                loop.create_task(collect_data(ap_handles[APID]))

                if ap_handles[APID].rate_control_alg == "minstrel_ht_kernel_space":
                    pass
                elif ap_handles[APID].rate_control_alg == "minstrel_ht_user_space":
                    pass
                elif ap_handles[APID].rate_control_alg == "param-setting-exp":
                    ap_handles[APID].rate_control_handle = mexman.MExRC(
                        ap_handles[APID].rate_control_settings
                    )
                    if "rate_control_interval" in ap_handles[APID].rate_control_settings:
                        loop.create_task(
                            ap_handles[APID].rate_control_handleexecute_rate_control(
                                ap_handles[APID],
                                ap_handles[APID].rate_control_settings[
                                    "rate_control_interval"
                                ],
                            )
                        )
                    else:
                        loop.create_task(
                            ap_handles[APID].rate_control_handle.execute_rate_control(
                                ap_handles[APID]
                            )
                        )
        loop.create_task(retry_conn(ap_handles))
    else:
        logging.error("Couldn't connect to any access points!")


async def retry_conn(ap_handles, retry_conn_duration=600):
    """


    Parameters
    ----------
    ap_handles : TYPE
        DESCRIPTION.
    retry_conn_duration : TYPE, optional
        DESCRIPTION. The default is 600.

    Returns
    -------
    None.

    """

    while True:
        try:
            await asyncio.sleep(retry_conn_duration)
            await reconn_ap_list(ap_handles)
        except (ValueError, KeyboardInterrupt):
            break


async def reconn_ap_list(ap_handles):
    """


    Parameters
    ----------
    ap_handles : TYPE
        DESCRIPTION.
    loop : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    loop = asyncio.get_running_loop()
    for APID in list(ap_handles.keys()):
        ap_handle = ap_handles[APID]
        if not ap_handle.connection:
            await ap_handle.connect_AP()
            if ap_handle.connection:
                ap_handle.start_radios()
                if not ap_handle.once_connected:
                    ap_handle.once_connected = True
                    loop.create_task(collect_data(ap_handle))
                else:
                    await remove_headers(ap_handle)

    pass


async def collect_data(ap_handle, reconn_time=600):
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
            reader = ap_handle.reader
            file_handle = ap_handle.file_handle

            data_line = await asyncio.wait_for(reader.readline(), reconn_time)
            data_line = data_line.decode("utf-8")
            if not len(data_line):
                ap_handle.connection = False
            else:
                try:
                    manage_line.process_line(ap_handle, data_line)
                    file_handle.write(data_line)
                except (ValueError, KeyboardInterrupt):
                    pass

        except KeyboardInterrupt:
            break

        except (OSError, ConnectionError, asyncio.TimeoutError):
            ap_handle.connection = False
            logging.error("Disconnected from {}".format(ap_handle.AP_ID))
            temp_ap_dict = {}
            temp_ap_dict[ap_handle.AP_ID] = ap_handle
            await reconn_ap_list(temp_ap_dict)
            continue


async def remove_headers(ap_handle):
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
            reader = ap_handle.reader
            fileHandle = ap_handle.file_handle

            data_line = await asyncio.wait_for(reader.readline(), timeout=1)

            if not len(data_line):
                ap_handle.connection = False
                logging.error("Disconnected from {}".format(ap_handle.AP_ID))
                temp_ap_dict = {}
                temp_ap_dict[ap_handle.AP_ID] = ap_handle
                await reconn_ap_list(temp_ap_dict)
                break
            else:
                line = data_line.decode("utf-8")
                if line[0] != "*":
                    fileHandle.write(line)
                    break

        except (OSError, ConnectionError, asyncio.TimeoutError) as error_type:

            ap_handle.connection = False
            logging.error(
                "Disconnected from {} -> {}".format(ap_handle.AP_ID, error_type)
            )
            temp_ap_dict = {}
            temp_ap_dict[ap_handle.AP_ID] = ap_handle
            await reconn_ap_list(temp_ap_dict)
            break

    pass


def setup_data_dir(output_dir):
    """


    Parameters
    ----------
    output_dir : TYPE
        DESCRIPTION.

    Returns
    -------
    output_dir : TYPE
        DESCRIPTION.

    """

    if len(output_dir) == 0:
        if not os.path.exists("data"):
            os.mkdir("data")
        output_dir = os.path.join(os.getcwd(), "data")

    return output_dir


def _check_net_conn(ap_handles: list):
    """
    This async function check if any of the AP in ap_handles has been sucessfully
    connected. If not then rateman terminates.

    Parameters
    ----------
    ap_handles : dictionary
        contains each AP in the network as key with relevant parameters

    Returns
    -------
    True: If there is atleast one active connection in ap_handles
    False: If none of the APs were connected

    """

    for APID in list(ap_handles.keys()):
        if ap_handles[APID].connection is True:
            return True

    return False
