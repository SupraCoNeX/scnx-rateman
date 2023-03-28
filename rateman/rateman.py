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
                                                                        List of AccessPoint objects for a give list of APs proved
                                                                        via CLI or a .csv file.
        rate_control_alg : str, optional
                                                                        Rate control algorithm to be executed.
                                                                        The default is "minstrel_ht_kernel_space".
        loop : asyncio.BaseEventLoop, optional
                                                                        Externally existing event loop passed to RateMan meant to be
                                                                        utilized gathering and executing asyncio tasks.
                                                                        The default is None.
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

    def add_task(self, coro, name=""):
        for task in self._tasks:
            if task.get_name() == name:
                return
        task = self._loop.create_task(coro, name=name)
        task.add_done_callback(self._tasks.remove)
        self._tasks.append(task)

    async def connect_ap(self, ap, timeout=5, reconnect=False, skip_api_header=False):
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
        radio_config : bool
                                                                        Flag indicating whether this is the first connection attempt. If set to
                                                                        True the timeout is ignored
        skip_api_header : bool
                                                                        Flag indicating whether this is the first connection attempt. If set to
                                                                        True the timeout is ignored
        """
        if not ap.loop:
            ap.loop = self._loop

        if reconnect:
            await asyncio.sleep(timeout)
        else:
            self._accesspoints[ap.name] = ap

        while not ap.connected:
            try:
                await ap.connect()
                if not ap.connected:
                    await asyncio.sleep(timeout)

            except (KeyboardInterrupt, asyncio.CancelledError):
                break

        if not skip_api_header:
            await asyncio.wait_for(process_header(ap), timeout=2)

        ap.set_rc_info(False)
        for radio in ap.radios:
            ap.apply_system_config(radio)
            ap.dump_stas(radio)
            ap.set_rc_info(True, radio)

        self.add_task(
            self.collect_data(ap, reconnect_timeout=timeout),
            name=f"collector_{ap.name}",
        )

    def reconnect_ap(self, ap, timeout):
        self.add_task(
            self.connect_ap(
                ap,
                timeout,
                reconnect=True,
            ),
            name=f"reconnect_{ap.name}",
        )

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

        try:
            async for data in ap:
                try:
                    line = data.decode("utf-8").rstrip()
                    for cb in self._raw_data_callbacks:
                        cb(ap, line)

                    line_type, fields = process_line(ap, line)

                    if not fields:
                        continue
                    elif line_type == "sta":
                        if fields[3] in ["add", "dump"]:
                            sta = parse_sta(ap.supp_rates, fields)
                            if ap.add_station(sta):
                                rc_task = ap.apply_sta_rate_control(sta)
                                if rc_task:
                                    self.add_task(
                                        rc_task,
                                        name=f"rc_{ap.name}_{sta.radio}_{sta.mac_addr}",
                                    )
                        elif fields[3] == "remove":
                            ap.remove_station(mac=fields[4], radio=fields[0])
                    self.execute_callbacks(ap, fields)
                except (UnicodeError, ValueError):
                    continue
        except (IOError, ConnectionError):
            ap.connected = False
            self._logger.error(f"Disconnected from {ap.name}")
            self.reconnect_ap(ap, reconnect_timeout)
        except (asyncio.CancelledError, KeyboardInterrupt):
            return

    async def stop(self):
        """
        Gracefully stop all asyncio tasks created and executed by RateMan and close all
        file objects.

        """
        for _, ap in self._accesspoints.items():
            if not ap.connected:
                continue
            ap.set_rc_info(False)
            ap.enable_auto_mode()
            await ap.disconnect()

        for task in self._tasks:
            self._logger.debug(f"Cancelling {task.get_name()}")
            task.cancel()

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
