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
from .accesspoint import AccessPoint
from .parsing import *

__all__ = ["RateMan"]


class RateMan:
    def __init__(self, loop=None, logger=None):
        """
        Parameters
        ----------
        loop : asyncio.BaseEventLoop, optional
            The event loop to execute on. A new loop will be created if none is
            provided.
        logger : logging.Logger
            The logger to use. A new one will be created if none is provided.
        """

        if not logger:
            self._logger = logging.getLogger("rateman")
        else:
            self._logger = logger

        if not loop:
            self._logger.debug("Creating new event loop")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._new_loop_created = True
        else:
            self._loop = loop
            self._new_loop_created = False

        self._tasks = []
        self._raw_data_callbacks = []
        self._data_callbacks = {
            "any": [],
            "txs": [],
            "stats": [],
            "rxs": [],
            "sta": [],
            "best_rates": [],
            "sample_rates": []
        }

        self._accesspoints = dict()

    @property
    def accesspoints(self) -> dict:
        return self._accesspoints

    @property
    def tasks(self) -> list:
        return self._tasks

    def get_sta(self, mac):
        for ap in self._accesspoints:
            sta = ap.get_sta(mac)
            if sta:
                return sta

        return None

    def add_task(self, coro, name=""):
        for task in self._tasks:
            if task.get_name() == name:
                return

        self._logger.debug(f"starting task '{name}'")

        task = self._loop.create_task(coro, name=name)
        task.add_done_callback(self.remove_task)
        self._tasks.append(task)
        return task

    def remove_task(self, task):
        if task in self._tasks:
            self._tasks.remove(task)

    def add_accesspoint(self, ap):
        if ap._addr in self._accesspoints:
            return

        self._accesspoints[ap._addr] = ap

        if not ap.loop:
            ap.loop = self._loop

    async def initialize(self, timeout=5):
        """
        Establish connections to acess points and process the information they
        provide. When this function returns, rateman has created representations
        of the accesspoints' radios, their state and capabilities, virtual
        interfaces, and connected stations.

        Parameters
        ----------
        timeout : int
            The timeout for the connection attempt. This is also the time that rateman will wait
            before making a new connection attempt.
        """

        await asyncio.wait([
            self.add_task(self.connect_ap(ap, timeout=timeout))
            for _,ap in self._accesspoints.items()
        ])

        for _,ap in self._accesspoints.items():
            if not ap.connected:
                self._logger.warning(
                    f"Connection to {ap} could not be established. Retrying in {timeout}s"
                )

    async def connect_ap(self, ap, timeout=5):
        try:
            async with asyncio.timeout(timeout):
                await ap.start_task(ap.connect(), f"connect_{ap.name}")
                if not ap.connected:
                    return

                await ap.start_task(process_header(ap), f"parse_api_info_{ap.name}")
                ap.start_task(self.rcd_connection(ap), f"rcd_{ap.name}")
        except (IOError, ConnectionError, asyncio.TimeoutError):
            ap.connected = False
            await self.reconnect_ap(ap, timeout)
        except asyncio.CancelledError as e:
            if ap.connected:
                await ap.disconnect()
            raise e

    async def reconnect_ap(self, ap, delay):
        if delay:
            await asyncio.sleep(delay)

        self.add_task(self.connect_ap(ap), name=f"reconnect_{ap.name}")

    def add_raw_data_callback(self, cb, context=None):
        """
        Register a callback to be called on unvalidated incoming data.
        """
        if (cb, context) not in self._raw_data_callbacks:
            self._raw_data_callbacks.append((cb, context))

    def add_data_callback(self, cb, type="any", context=None):
        """
        Register a callback to be called on incoming data.

        Parameters
        ----------
        cb : Callable
            The callback function.
        type : str
            Which data to call the callback on. Valid options: _any, txs, stats,
            rxs, sta, best_rates,_ or _sample_rates_.
        context : object
            Additional arguments to be passed to the callback on invocation.
        """
        if type not in self._data_callbacks.keys():
            raise ValueError(type)

        for (c, _) in self._data_callbacks[type]:
            if c == cb:
                return

        self._data_callbacks[type].append((cb, context))

    def remove_data_callback(self, cb):
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

    def execute_callbacks(self, ap, fields):
        for (cb, ctx) in self._data_callbacks["any"]:
            cb(ap, fields, context=ctx)

        for (cb, ctx) in self._data_callbacks[fields[2]]:
            cb(ap, *fields, context=ctx)

    async def rcd_connection(self, ap, reconnect_timeout=10):
        """
        Receive data from an instance of minstrel-rcd. Reconnect if connection
        is lost.

        Parameters
        ----------
        ap : AccessPoint
            The AP to receive the data from.
        reconnect_timeout : float
            Seconds to wait before attempting to reconnect to a disconnected AP.
        Returns
        -------
        None.

        """

        self._logger.debug(f"Starting RC data collection from {ap}")
        ap.set_rc_info(True)

        try:
            async for line in ap.rc_data():
                for (cb, ctx) in self._raw_data_callbacks:
                    cb(ap, line, context=ctx)

                line_type, fields = process_line(ap, line)

                if not fields:
                    continue

                if line_type == "sta":
                    # TODO: handle sta;update
                    if fields[3] in ["add", "dump"]:
                        ap.add_station(parse_sta(ap, fields))
                    elif fields[3] == "remove":
                        sta = ap.remove_station(mac=fields[4], radio=fields[0])
                        if sta:
                            await sta.stop_rate_control()
                self.execute_callbacks(ap, fields)
        except (IOError, ConnectionError):
            ap.connected = False
            self._logger.error(f"Disconnected from {ap.name}")
            await self.reconnect_ap(ap, reconnect_timeout)
        except asyncio.CancelledError as e:
            raise e

    async def stop(self):
        """
        Gracefully stop all asyncio tasks created and executed by RateMan and
        close all file objects.

        """
        self._logger.debug("Stopping RateMan")

        for task in self._tasks:
            self._logger.debug(f"Cancelling task '{task.get_name()}'")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._logger.debug(f"Disconnecting APs")

        for _, ap in self._accesspoints.items():
            if not ap.connected:
                continue

            ap.set_rc_info(False)
            for radio in ap.radios:
                for sta in ap.get_stations(radio):
                    await sta.stop_rate_control()

                ap.enable_auto_mode(radio)

            await ap.disconnect()

        if self._new_loop_created:
            self._loop.close()

        self._logger.debug("RateMan stopped")

if __name__ == "__main__":

    def parse_aps(apstrs):
        aps = []

        for apstr in apstrs:
            fields = apstr.split(":")
            if len(fields) < 2:
                print(f"Inval access point: '{apstr}'", file=sys.stderr)
                continue

            name = fields[0]
            addr = fields[1]

            try:
                rcd_port = int(fields[2])
            except (IndexError, ValueError):
                rcd_port = 21059

            aps.append(AccessPoint(name, addr, rcd_port))

        return aps

    # Exec: python rateman.py minstrel_ht_user_space AP1:192.168.23.4 AP2:192.46.34.23 -A ../../demo/sample_ap_lists/local_test.csv
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "algorithm",
        type=str,
        choices=["minstrel_ht_kernel_space", "minstrel_ht_user_space"],
        default="minstrel_ht_kernel_space",
        help="Rate control algorithm to run.",
    )
    arg_parser.add_argument(
        "-A",
        "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: NAME,ADDR,RCDPORT.",
    )
    arg_parser.add_argument(
        "accesspoints",
        metavar="AP",
        nargs="*",
        type=str,
        help="Accesspoint to connecto to. Format: 'NAME:ADDR:RCDPORT'. "
        + "RCDPORT is optional and defaults to 21059.",
    )
    args = arg_parser.parse_args()
    aps = parse_aps(args.accesspoints)

    if args.ap_file:
        aps += accesspoint.from_file(args.ap_file)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print("Running rateman...")
    rateman = RateMan(aps, loop=loop)

    # add a simple print callback to see the incoming data
    rateman.add_data_callback(lambda ap, line, _: print(f"{ap.name}> '{line}'"))

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman.stop())
        print("DONE")
