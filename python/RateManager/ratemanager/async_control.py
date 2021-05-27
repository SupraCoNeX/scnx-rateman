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


__all__ = ["recv_data", "set_rate", "stop_trigger", "init_data_parsing",
           "monitoring_tasks",
           "main_AP_tasks"]


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

    ap_connection_task_list = []
    ap_data_parsing_task_list = []
    ap_readers = []
    ap_writers = []

    fileHandles = []

    for APID in APIDs:

        fileHandle = open("collected_data/data_" + APID + ".csv", "w")
        print("Data file created for", APID)

        fileHandles.append(fileHandle)

        reader, writer = await asyncio.open_connection(APInfo[APID]['IPADD'],
                                                       APInfo[APID]['PORT'])

        ap_readers.append(reader)
        ap_writers.append(writer)

    init_data_parsing(ap_writers)

    monitoring_tasks(ap_readers, fileHandles, loop)

    loop.create_task(set_rate(ap_writers))

    loop.create_task(stop_trigger(ap_readers, ap_writers, fileHandles, loop))


def init_data_parsing(ap_writers):

    print('starting radios')
    cmd = "phy1;start;stats;txs"

    for writer in ap_writers:
        writer.write(cmd.encode("ascii") + b"\n")


def monitoring_tasks(ap_readers, fileHandles, loop):

    for reader, fileHandle in zip(ap_readers, fileHandles):

        loop.create_task(recv_data(reader, fileHandle))


async def recv_data(reader, fileHandle):
    try:
        while True:
            await asyncio.sleep(0.01)
            dataLine = await reader.readline()
            print('parsing data')
            fileHandle.write(dataLine.decode("utf-8"))
    except KeyboardInterrupt:
        pass
    reader.close()


async def set_rate(ap_writers):
    try:
        while True:
            await asyncio.sleep(0.01)
            rate_ind = np.random.randint(0, 15)
            print("setting rate now")
            # writer.write(("phy1;setr;rate_1:mcs"+str(rate_ind)).encode())
            # await writer.drain()
    except KeyboardInterrupt:
        pass
    writer.close()


async def stop_trigger(ap_readers, ap_writers, fileHandles, loop):
    timeout = 1
    prompt = 'To stop RateMan, enter x.\n'
    cmd = "phy1;stop"

    try:
        while True:
            await asyncio.sleep(0.2)
            answer = timedInput(prompt, timeout)

            if answer == 'x':
                print('RateMan will stop now.')

                for reader, writer, fileHandle in zip(ap_readers, ap_writers, fileHandles):
                    writer.write(cmd.encode("ascii") + b"\n")
                    # writer.close()
                    # fileHandle.close()
                for task in asyncio.all_tasks():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                            print("task is cancelled now")    
                loop.stop()
                # stop_tasks(loop)
                   
    except KeyboardInterrupt:
        pass
    loop.stop()

def stop_tasks(loop):
    for task in asyncio.all_tasks():
       task.cancel()

   