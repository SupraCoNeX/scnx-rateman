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

import asyncio
import os
import logging
import parsing
# import mexman

__all__ = [
    "connect_ap",
    "collect_data",
    "skip_api_header",
]

async def connect_ap(rateman, ap, timeout, reconnect=False, skip_api_header=False):
    """
    Attempt to connect to the given AP after waiting timeout seconds.
    On successful connection a data collection task is scheduled.

    Parameters
    ----------
    rateman : RateMan
        The rateman instance managing this task.
    ap : AccessPoint
        The AP to connect to.
    timeout : float
        How many seconds to wait before attempting the connection.
    reconnect : bool
        Flag indicating whether this is the first connection attempt. If set to
        True the timeout is ignored
    skip_api_header : bool
        When set to True rateman is not notified of incoming API data
    """

    if reconnect:
        await asyncio.sleep(timeout)

    while not ap.connected:
        await ap.connect()
        await asyncio.sleep(timeout)

    if skip_api_header:
        ap.enable_rc_api()
        await skip_api_header(rateman, ap)
        if not ap.connected:
            rateman.add_task(
                connect_ap(rateman, ap, timeout, reconnect=True, skip_api_header=True), 
                name=f"reconnect_{ap.id}"
            )
            return

    rateman.add_task(
        collect_data(rateman, ap, reconnect_timeout=timeout),
         name=f"collector_{ap.id}"
    )

async def collect_data(rateman, ap, reconnect_timeout=10):
    """
    Receive data from an instance of minstrel-rcd notifying rateman of new data and attempting to
    reconnect on connection failure.

    Parameters
    ----------
    rateman : RateMan
        The rateman instance managing this task.
    ap : AccessPoint
        The AP to receive the data from.
    reconnect_timeout : float
        Seconds to wait before attempting to reconnect to a disconnected AP.
    Returns
    -------
    None.

    """
    while True:
        try:
            line = await asyncio.wait_for(ap.reader.readline(), 0.01)
            rateman.process_line(ap, line.decode("utf-8").rstrip("\n"))
        except (KeyboardInterrupt, asyncio.CancelledError):
            break
        except (asyncio.TimeoutError, UnicodeError):
            await asyncio.sleep(0.01)
        except ConnectionError:
            ap.connected = False
            logging.error(f"Disconnected from {ap.id}")

            # FIXME: we might be setting skip to True prematurely here. Maybe we need a flag
            #        indicating whether the API header has been received completely for an AP.
            rateman.add_task(
                connect_ap(rateman, ap, reconnect_timeout, reconnect=True, skip_api_header=True),
                name=f"reconnect_{ap.id}"
            )
            break


async def skip_api_header(rateman, ap):
    """
    Receive data from an instance of minstrel-rcd without notifying rateman of
    minstrel-rcd API header lines. Once a non-API line is received, rateman
    is notified and this coroutine terminates. This is to avoid processing API
    headers again after reconnecting to a previously connected AP.

    Parameters
    ----------
    rateman : RateMan
        The rateman instance managing this task.
    ap : AccessPoint
        The AP to receive the data from.
    Returns
    -------
    None.

    """
    while True:
        try:
            data_line = await asyncio.wait_for(ap.reader.readline(), timeout=0.01)

            if not len(data_line):
                ap.connected = False
                logging.error(f"Disconnected from {ap.id}")
                break

            line = data_line.decode("utf-8").rstrip("\n")

            if line[0] != "*":
                rateman.process_line(ap, line)
                break
        except (OSError, ConnectionError, asyncio.TimeoutError) as error:
            logging.error(f"Disconnected from {ap.id}: {error}")
            ap.connected = False
            break
