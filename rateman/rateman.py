# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import logging
import asyncio
import traceback
from contextlib import suppress
import os
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

    async def ap_connection(self, ap: AccessPoint, path, timeout=5):
        ap_header_path = os.path.join(path, f"{ap.name}_orca_header.csv")
        while True:
            self._logger.debug(f"Connecting to {ap}, timeout={timeout} s")
            try:
                async with asyncio.timeout(timeout):
                    await ap.connect()
                    if not ap.header_collected:
                        await process_header(ap, path=ap_header_path)
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

    async def rcd_connection(self, ap: AccessPoint):
        try:
            async for line in ap.events():
                await process_line(ap, line)
        except asyncio.CancelledError as e:
            raise e

    async def initialize(
        self,
        path: str = None,
        timeout: int = 5,
    ):
        """
        Establish connections to access points and process the information they provide. When this
        function returns, rateman has created representations of the accesspoints' radios, their
        state and capabilities, virtual interfaces, and connected stations.

        Parameters
        ----------
        path: str
            Directory path to save ORCA header.

        timeout : int
            The timeout for the connection attempt. This is also the time that rateman will wait
            before making a new connection attempt.
        """
        if not path:
            path = os.getcwd()
        tasks = [
            self._loop.create_task(
                self.ap_connection(ap, path, timeout=timeout), name=f"connect_{ap.name}"
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
                await sta.start_rate_control(
                    "minstrel_ht_kernel_space", {"update_freq": 20, "sample_freq": 50}
                )

            await ap.disconnect()
            rcd_connection.cancel()
            with suppress(asyncio.CancelledError):
                await rcd_connection

        self._accesspoints = {}

        if self._new_loop_created:
            self._loop.close()

        self._logger.debug("RateMan stopped")
