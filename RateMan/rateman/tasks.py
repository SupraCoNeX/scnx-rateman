# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Manage Asynchronous I/O Tasks
-----------------------------

This is the class that provides functions to collect and manage user callbacks 
and asyncio tasks. Includes basic methods to collect data from Rate Control API.

"""

import asyncio
import logging
from .parsing import *

__all__ = ["TaskMan"]


class TaskMan:
    def __init__(self, loop):
        """
        Parameters
        ----------
        loop : asyncio.BaseEventLoop
            Current event loop passed by RateMan instance utilized for
            gathering and executing asyncio tasks.

        """
        self._loop = loop
        self._tasks = []
        self._data_callbacks = [process_line]

    @property
    def tasks(self) -> list:
        return self._tasks

    @property
    def cur_loop(self) -> asyncio.BaseEventLoop():
        return self._loop

    def add_task(self, coro, name=""):
        for task in self._tasks:
            if task.get_name() == name:
                return

        task = self._loop.create_task(coro, name=name)
        task.add_done_callback(self._tasks.remove)
        self._tasks.append(task)

    # TODO: differentiate by line type
    def add_data_callback(self, cb):
        """
        Register a callback to be called on incoming data.
        """
        if cb not in self._data_callbacks:
            self._data_callbacks.append(cb)

    def remove_data_callback(self, cb):
        """
        Unregister a data callback.
        """
        if cb in self._data_callbacks:
            self._data_callbacks.remove(cb)

    def execute_callbacks(self, ap, line):

        for cb in self._data_callbacks:
            cb(ap, line)

    async def connect_ap(self, ap, timeout, reconnect=False, skip_api_header=False):
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
            await self.skip_header_lines(ap)
            if not ap.connected:
                self.add_task(
                    self.connect_ap(ap, timeout, reconnect=True, skip_api_header=True),
                    name=f"reconnect_{ap.ap_id}",
                )
                return

        self.add_task(
            self.collect_data(ap, reconnect_timeout=timeout),
            name=f"collector_{ap.ap_id}",
        )

        if ap.rate_control_alg != "minstrel_ht_kernel_space":
            self.add_task(ap.rate_control(ap, self._loop), name=f"rc_{ap.ap_id}")

    async def collect_data(self, ap, reconnect_timeout=10):
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

                if not len(line):
                    print("Raising Connection Error")
                    raise ConnectionError

                self.execute_callbacks(ap, line.decode("utf-8").rstrip("\n"))

                if ap.save_data:
                    ap.data_file.write(line.decode("utf-8"))

            except (KeyboardInterrupt, asyncio.CancelledError):
                break
            except (asyncio.TimeoutError, UnicodeError):
                await asyncio.sleep(0.01)
            except ConnectionError:
                ap.connected = False
                logging.error(f"Disconnected from {ap.ap_id}")

                # FIXME: we might be setting skip to True prematurely here. Maybe we need a flag
                #        indicating whether the API header has been received completely for an AP.
                self.add_task(
                    self.connect_ap(
                        ap, reconnect_timeout, reconnect=True, skip_api_header=True
                    ),
                    name=f"reconnect_{ap.ap_id}",
                )
                break

    async def skip_header_lines(ap):
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
                    logging.error(f"Disconnected from {ap.ap_id}")
                    break

                line = data_line.decode("utf-8").rstrip("\n")

                if line[0] != "*":
                    process_line(ap, line)
                    break
            except (OSError, ConnectionError, asyncio.TimeoutError) as error:
                logging.error(f"Disconnected from {ap.ap_id}: {error}")
                ap.connected = False
                break
