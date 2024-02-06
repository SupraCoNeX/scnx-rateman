# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import argparse
import sys
import os
import logging
import asyncio
import importlib
import csv
import traceback
from contextlib import suppress

from .accesspoint import AccessPoint
from .station import Station
from .parsing import *
from .exception import UnsupportedAPIVersionError

__all__ = ["RateMan"]


class RateMan:
    """

    :ivar asyncio.BaseEventLoop loop:   The event loop on which rateman is to run. If none is
                                        provided, a new one will be created.
    :ivar logging.Logger logger:    The logger for this rateman instance. If none is given, a new
                                    one will be created.
    """

    def __init__(self, loop=None, logger=None):
        self._logger = logger if logger else logging.getLogger("rateman")

        if not loop:
            self._logger.debug("Creating new event loop")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._new_loop_created = True
        else:
            self._loop = loop
            self._new_loop_created = False

        self._raw_data_callbacks = []
        self._data_callbacks = {
            "stats": [],
            "rxs": [],
            "sta": [],
            "best_rates": [],
            "sample_rates": [],
        }

        self._accesspoints = dict()

    @property
    def accesspoints(self) -> list[AccessPoint]:
        """
        Return the list of registered :class:`.AccessPoint` s.
        """
        return [ap for _, (ap, _) in self._accesspoints.items()]

    def add_accesspoint(self, ap: AccessPoint):
        """
        Register the given :class:`.AccessPoint` instance with rateman.
        """
        if (ap._addr, ap._rcd_port) in self._accesspoints:
            return

        self._accesspoints[(ap._addr, ap._rcd_port)] = (ap, None)

        if not ap.loop:
            ap.loop = self._loop

    def get_sta(self, mac: str) -> Station:
        """
        Return the :class:`.Station` object identified by the given MAC address.
        """
        for ap in self._accesspoints:
            sta = ap.get_sta(mac)
            if sta:
                return sta

        return None

    async def ap_connection(self, ap: AccessPoint, timeout=5):
        while True:
            self._logger.debug(f"Connecting to {ap}, timeout={timeout} s")

            try:
                async with asyncio.timeout(timeout):
                    await ap.connect()
                    await process_header(ap)
                    break
            except asyncio.CancelledError as e:
                raise e
            except UnsupportedAPIVersionError as e:
                await ap.disconnect()
                self._logger.error(f"Diconnected from {ap}: {e}")
                raise e
            except Exception as e:
                tb = traceback.extract_tb(e.__traceback__)[-1]
                self._logger.error(
                    f"{ap}: Disconnected. Trying to reconnect in {timeout}s: "
                    f"Error='{e}' ({tb.filename}:{tb.lineno})"
                )
                await asyncio.sleep(timeout)
                continue

    def add_raw_data_callback(self, cb, context=None):
        """
        Register a callback to be called on unvalidated incoming ORCA event data.

        Parameters
        ----------
        cb : callable
            The callback function.
        context : object
            Additional arguments to be passed to the callback function.
        """
        if (cb, context) not in self._raw_data_callbacks:
            self._raw_data_callbacks.append((cb, context))

    def add_data_callback(self, cb, type: str, context=None):
        """
        Register a callback to be called on incoming ORCA event data.

        Parameters
        ----------
        cb : callable
            The callback function.
        type : str
            Which data to call the callback on. Valid options: `"stats",
            "rxs", "sta", "best_rates", or "sample_rates"`.
        context : object
            Additional arguments to be passed to the callback function.
        """
        if type not in self._data_callbacks.keys():
            raise ValueError(type)

        for (c, _) in self._data_callbacks[type]:
            if c == cb:
                return

        self._data_callbacks[type].append((cb, context))

    def remove_data_callback(self, cb: callable):
        """
        Unregister a data callback.
        """
        for (c, ctx) in self._raw_data_callbacks:
            if c == cb:
                self._raw_data_callbacks.remove((c, ctx))
                return

        for _, cbs in self._data_callbacks.items():
            for (c, ctx) in cbs:
                if c == cb:
                    cbs.remove((c, ctx))
                    break

    def execute_callbacks(self, ap: AccessPoint, fields: list[str]):
        try:
            for (cb, ctx) in self._data_callbacks[fields[2]]:
                cb(ap, *fields, context=ctx)
        except KeyError:
            return

    async def rcd_connection(self, ap: AccessPoint):
        try:
            async for line in ap.events():
                if (fields := await process_line(ap, line)) is not None:
                    # FIXME: maybe we should move the callback logic into the AP, have it at a
                    # per-AP basis. Then execute_callbacks() could happen as a part of
                    # process_line() in the AP object.
                    self.execute_callbacks(ap, fields)
        except asyncio.CancelledError as e:
            raise e

    async def initialize(self, timeout: int = 5):
        """
        Establish connections to access points and process the information they provide. When this
        function returns, rateman has created representations of the accesspoints' radios, their
        state and capabilities, virtual interfaces, and connected stations.

        Parameters
        ----------
        timeout : int
            The timeout for the connection attempt. This is also the time that rateman will wait
            before making a new connection attempt.
        """

        tasks = [
            self._loop.create_task(
                self.ap_connection(ap, timeout=timeout), name=f"connect_{ap.name}"
            )
            for ap in self.accesspoints
        ]

        done, pending = await asyncio.wait(tasks, timeout=timeout)
        for task in pending:
            with suppress(asyncio.CancelledError):
                task.cancel()
                await task

        for task in done:
            if task.exception():
                self._logger.error(f"{task.exception()}")

        for (addr, port), (ap, _) in self._accesspoints.items():
            if ap.connected:
                rcd_task = self._loop.create_task(self.rcd_connection(ap), name=f"rcd_{ap.name}")
                self._accesspoints.update({(addr, port): (ap, rcd_task)})
            else:
                self._logger.warning(
                    f"Connection to {ap} could not be established in time (timeout={timeout}s)"
                )

    async def stop(self):
        """
        Stop all running tasks and disconnect from all accesspoints. Kernel rate control will be
        enabled for all the access points' stations prior to disconnection.
        """
        self._logger.debug("Stopping RateMan")

        for _, (ap, rcd_connection) in self._accesspoints.items():
            if not ap.connected:
                continue

            stas = []
            for radio in ap.radios:
                stas += [sta for sta in ap.stations(radio) if sta.associated]
                await ap.disable_events(radio, ap.enabled_events(radio))

            for sta in stas:
                print(sta.mac_addr)
                await sta.start_rate_control(
                    "minstrel_ht_kernel_space",
                    {"update_freq": 20, "sample_freq": 50}
                )

            await ap.disconnect()
            rcd_connection.cancel()
            with suppress(asyncio.CancelledError):
                await rcd_connection

        self._accesspoints = {}

        if self._new_loop_created:
            self._loop.close()

        self._logger.debug("RateMan stopped")
