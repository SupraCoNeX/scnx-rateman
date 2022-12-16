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
from .parsing import process_line, process_phy_info

__all__ = ["TaskMan"]


class TaskMan:
    def __init__(self, loop, logger):
        """
        Parameters
        ----------
        loop : asyncio.BaseEventLoop
            Current event loop passed by RateMan instance utilized for
            gathering and executing asyncio tasks.

        """
        self._loop = loop
        self._logger = logger
        self._tasks = []
        self._raw_data_callbacks = []
        self._data_callbacks = {
            "any": [],
            "txs": [],
            "stats": [],
            "rxs": [],
            "sta": [],
            "best_rates": []
        }

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
        return task

    def add_raw_data_callback(self, cb):
        """
        Register a callback to be called on unvalidated incoming data
        """
        if cb not in self._raw_data_callbacks:
            self._raw_data_callbacks.append(cb)

    def add_data_callback(self, cb, type="any", args=None):
        """
        Register a callback to be called on incoming data.
        """
        if type not in self._data_callbacks.keys():
            raise ValueError(type)

        for (c, _) in self._data_callbacks[type]:
            if c == cb:
                return

        self._data_callbacks[type].append((cb, args))

    def remove_data_callback(self, cb):
        """
        Unregister a data callback.
        """
        for (c, a) in self._raw_data_callbacks:
            if c == cb:
                self._raw_data_callbacks.remove((c, a))
                return

        for _, cbs in self._data_callbacks.items():
            for (c, a) in cbs:
                if c == cb:
                    cbs.remove((c, a))
                    break

    def execute_callbacks(self, ap, fields):
        for (cb, args) in self._data_callbacks["any"]:
            cb(ap, fields, args)

        for (cb, args) in self._data_callbacks[fields[2]]:
            cb(ap, *fields, args=args)

    async def connect_ap(
        self,
        ap,
        timeout=5,
        reconnect=False,
        radio_config=None
    ):
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

        line = await self.process_header(ap)
        if not line and not ap.connected:
            return # TODO: handle disconnect
        elif line:
            process_line(ap, line)

        ap.set_rc_info(False)

        if radio_config:
            for radio,cfg in radio_config.items():
                ap.apply_radio_config(radio, cfg)

        ap.set_rc_info(True)

        for rc_task in ap.apply_rate_control():
            if rc_task:
                self.add_task(rc_task, name=f"rc_{ap.name}")

        self.add_task(
            self.collect_data(ap, reconnect_timeout=timeout),
            name=f"collector_{ap.name}",
        )

    async def collect_data(self, ap, reconnect_timeout=10):
        """
        Receive data from an instance of minstrel-rcd. Reconnect if connection
        is lost.

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
                data = await asyncio.wait_for(ap.reader.readline(), 0.01)
                line = data.decode("utf-8").rstrip()

                for cb in self._raw_data_callbacks:
                    cb(ap, line)

                fields = process_line(ap, line)
                if not fields:
                    continue

                self.execute_callbacks(ap, fields)

            except (KeyboardInterrupt, IOError, ValueError, asyncio.CancelledError):
                break
            except (asyncio.TimeoutError, UnicodeError):
                await asyncio.sleep(0.01)
            except (ConnectionError, TimeoutError):
                ap.connected = False
                self._logger.error(f"Disconnected from {ap.name}")

                # FIXME: we might be setting skip to True prematurely here. Maybe we need a flag
                #        indicating whether the API header has been received completely for an AP.
                self.add_task(
                    self.connect_ap(
                        ap, reconnect_timeout, reconnect=True, skip_api_header=True
                    ),
                    name=f"reconnect_{ap.name}",
                )
                break

    async def get_next_data_line(self, ap, timeout):
        data = await asyncio.wait_for(ap.reader.readline(), timeout=timeout)

        if data == "":
            ap.connected = False
            self._logger.error(f"Disconnected from {ap.name}")
            return None

        return data.decode("utf-8").rstrip()

    async def process_header(self, ap):
        # scroll past api header
        line = await self.skip_header_lines(ap)
        fields = line.split(";")

        try:
            while process_phy_info(ap, fields):
                line = await self.get_next_data_line(ap, 1)
                if not line:
                    return

                fields = line.split(";")
        except asyncio.TimeoutError:
            return

    async def skip_header_lines(self, ap):
        """
        Receive data from an instance of minstrel-rcd without notifying rateman of
        minstrel-rcd API header lines. Once a non-API line is received, rateman
        is notified and this coroutine terminates. This is to avoid processing API
        headers again after reconnecting to a previously connected AP.

        Parameters
        ----------
        ap : AccessPoint
            The AP to receive the data from.
        Returns
        -------
        The first non-API-header line

        """

        try:
            line = "*"

            while line[0] == "*":
                line = await self.get_next_data_line(ap, 1)
                if not line:
                    break

            return line
        except Exception as e:
            self._logger.error(f"Disconnected from {ap.name}: {e}")
            ap.connected = False
            return None