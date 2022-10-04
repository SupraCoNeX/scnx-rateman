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
import sys
import logging
from .parsing import process_line

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
        self._raw_data_callbacks = []
        self._data_callbacks = {"any": [], "txs": [], "stats": [], "rxs": [], "sta": []}

    @property
    def tasks(self) -> list:
        return self._tasks

    @property
    def cur_loop(self) -> asyncio.BaseEventLoop:
        return self._loop

    def add_task(self, coro, name=""):
        for task in self._tasks:
            if task.get_name() == name:
                return
        task = self._loop.create_task(coro, name=name)
        task.add_done_callback(self._tasks.remove)
        self._tasks.append(task)

    def add_raw_data_callback(self, cb):
        """
        Register a callback to be called on unvalidated incoming data
        """
        if cb not in self._raw_data_callbacks:
            self._raw_data_callbacks.append(cb)

    def add_data_callback(self, cb, type="any"):
        """
        Register a callback to be called on incoming data.
        """
        if type not in ["any", "txs", "rxs", "stats", "sta"]:
            raise ValueError(type)

        if cb not in self._data_callbacks[type]:
            self._data_callbacks[type].append(cb)

    def remove_data_callback(self, cb):
        """
        Unregister a data callback.
        """
        if cb in self._raw_data_callbacks:
            self._raw_data_callbacks.remove(cb)
            return

        for _, cbs in self._data_callbacks.items():
            if cb in cbs:
                cbs.remove(cb)

    def execute_callbacks(self, ap, fields):
        logging.debug(f"{ap.ap_id} > {';'.join(fields)}")

        for cb in self._data_callbacks["any"]:
            cb(ap, fields)

        for cb in self._data_callbacks[fields[2]]:
            try:
                cb(ap, *fields)
            except TypeError:
                print(
                    "Incorrect callback signature. Argument count must "
                    + "match the number of fields separated by ';' in the line",
                    file=sys.stderr,
                )

    async def connect_ap(self, ap, timeout = 5, reconnect=False, 
                         skip_api_header=False, 
                         **rate_control_options):
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
            try:
                await ap.connect()
                if not ap.connected:
                    await asyncio.sleep(timeout)
            except (KeyboardInterrupt, asyncio.CancelledError):
                break

        if skip_api_header:
            ap.enable_rc_api()
            await self.skip_header_lines(ap)
            if not ap.connected:
                self.add_task(
                    self.connect_ap(ap, timeout, reconnect=True, skip_api_header=True),
                    name=f"reconnect_{ap.ap_id}",
                )
                return

        if ap.connected:
            self.add_task(
                self.collect_data(ap, reconnect_timeout=timeout),
                name=f"collector_{ap.ap_id}",
            )

            if ap.rate_control and ap.rate_control_alg != "minstrel_ht_kernel_space":
                self.add_task(ap.rate_control(ap, self._loop,**rate_control_options), name=f"rc_{ap.ap_id}")

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

                # if not len(line):
                #     raise ConnectionError

                # do internal housekeeping first
                fields = process_line(ap, line.decode("utf-8").rstrip("\n"))

                # execute raw data callbacks on unvalidated line
                for cb in self._raw_data_callbacks:
                    cb(ap, line.decode("utf-8").rstrip("\n"))

                if ap.save_data:
                    ap.data_file.write(line.decode("utf-8"))

                if not fields:
                    continue

                self.execute_callbacks(ap, fields)

            except (KeyboardInterrupt, asyncio.CancelledError):
                break
            except (asyncio.TimeoutError, UnicodeError):
                await asyncio.sleep(0.01)
            except (ConnectionError, TimeoutError):
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

    async def skip_header_lines(self, ap):
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
