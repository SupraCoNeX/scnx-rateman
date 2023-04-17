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
    def __init__(self, aps=[], loop=None, logger=None):
        """
        Parameters
        ----------
        aps : list
            List of AccessPoint object to connect to.
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
        }

        self._accesspoints = dict()
        for ap in aps:
            self.add_task(
                self.connect_ap(ap),
                name=f"connect_{ap.name}",
            )

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
        task = self._loop.create_task(coro, name=name)
        self._tasks.append(task)

    def remove_task(self, name):
        if name in self._tasks:
            self._tasks.remove(name)

    async def connect_ap(self, ap, delay=None, skip_api_header=False):
        """
        Attempt to connect to the given AP after waiting delay seconds.
        On successful connection a data collection task is scheduled.

        Parameters
        ----------
        ap : AccessPoint
            The AP to connect to.
        delay : float
            How many seconds to wait before attempting the connection.
        skip_api_header : bool
            If set to True, the API info header will be ignored during the
            connection process.
        """
        if not ap.loop:
            ap.loop = self._loop

        if delay:
            await asyncio.sleep(delay)

        self._accesspoints[ap.name] = ap

        while not ap.connected:
            try:
                await ap.connect()
                if not ap.connected:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                break

        if not skip_api_header:
            await asyncio.wait_for(process_header(ap), timeout=2)

        for radio in ap.radios:
            ap.dump_stas(radio)
            ap.set_rc_info(True, radio)

        self.add_task(
            self.rcd_connection(ap, reconnect_timeout=5),
            name=f"rcd_{ap.name}",
        )

    def reconnect_ap(self, ap, delay):
        self.add_task(
            self.connect_ap(ap, delay=delay),
            name=f"reconnect_{ap.name}",
        )

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
        reconnect_delay : float
            Seconds to wait before attempting to reconnect to a disconnected AP.
        Returns
        -------
        None.

        """

        try:
            async for data in ap:
                try:
                    line = data.decode("utf-8").rstrip()
                    for (cb, ctx) in self._raw_data_callbacks:
                        cb(ap, line, context=ctx)

                    line_type, fields = process_line(ap, line)

                    if not fields:
                        continue
                    elif line_type == "sta":
                        if fields[3] in ["add", "dump"]:
                            sta = parse_sta(ap, fields)
                            if ap.add_station(sta):
                                rc_alg = ap.default_rc_alg
                                rc_opts = ap._default_rc_opts
                                rc = sta.set_rate_control(rc_alg, rc_opts)
                                if rc:
                                    rc_name = f"rc_{ap.name}_{sta.radio}_{sta.mac_addr}_{rc_alg}"
                                    self.add_task(rc, name=rc_name)

                        elif fields[3] == "remove":
                            sta = ap.remove_station(mac=fields[4], radio=fields[0])
                            if sta:
                                sta.stop_rate_control()
                    self.execute_callbacks(ap, fields)
                except (UnicodeError, ValueError):
                    continue
        except (IOError, ConnectionError):
            ap.connected = False
            self._logger.error(f"Disconnected from {ap.name}")
            self.reconnect_ap(ap, reconnect_timeout)
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
            ap.enable_auto_mode()
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
