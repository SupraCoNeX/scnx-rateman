#!/usr/bin/python3
# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Rate Manager Object
----------------

This class provides an object for Rate Manager that utilizes functions defined
in different modules. 

"""

import argparse
import sys
from datetime import datetime
import logging
import asyncio
import json
import os
from accesspoint import *
import tasks
import parsing
import time

__all__ = ["RateMan"]


class RateMan:
    def __init__(self, aps, rate_control_alg: str = "minstrel_ht_kernel_space", loop = None):
        if not loop:
            logging.info("Creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._new_loop_created = True
        else:
            self._new_loop_created = False

        self._loop = loop
        self._accesspoints = {}
        self._tasks = []
        self._data_callbacks = [parsing.process_line]

        for ap in aps:
            ap.rate_control_alg = rate_control_alg
            ap.rate_control = self.load_rc(rate_control_alg)
            self._accesspoints[ap.id] = ap
            self.add_task(tasks.connect_ap(self, ap, 5), name=f"connect_{ap.id}")

    @property
    def accesspoints(self) -> dict:
        return self._accesspoints

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

    def process_line(self, ap, line):
        logging.debug(f"{ap.id}> '{line}'")

        for cb in self._data_callbacks:
            cb(ap, line)

    def add_task(self, coro, name=""):
        for task in self._tasks:
            if task.get_name() == name:
                return

        task = self._loop.create_task(coro, name=name)        
        task.add_done_callback(self._tasks.remove)
        self._tasks.append(task)

    # async def initialize(self):
    #     for id, ap in self._accesspoints.items():
    #         await ap.connect()

    #         if ap.connected:
    #             ap.once_connected = True
    #             self.add_task(tasks.collect_data(self, ap), name=f"collector_{id}")

    #         if ap.rate_control_alg == "minstrel_ht_kernel_space":
    #             pass
    #         elif ap.rate_control_alg and ap.rate_control:
    #             self.add_task(ap.rate_control(ap), name=f"rc_{id}")
    #         # elif ap.rate_control_alg == "param-setting-exp":
    #         #     ap.rate_control = mexman.MExRC(ap.rate_control_settings)
    #         #     if "rate_control_interval" in ap.rate_control_settings:
    #         #         loop.create_task(
    #         #             ap.rate_control.execute_rate_control(
    #         #                 ap,
    #         #                 ap.rate_control_settings["rate_control_interval"],
    #         #             )
    #         #         )
    #         #     else:
    #         #         loop.create_task(ap.rate_control.execute_rate_control(ap))
    #     else:
    #         logging.error(f"Couldn't establish initial connection to {id}")
    #         self.add_task(tasks.reconnect_ap(self, ap, 5), name=f"reconnect_{id}")


    def start_measurement(self, output_dir: str = "") -> None:
        # TODO
        # start_time = time.time()
        # try:
        #     self._loop.run_forever()
        # except (OSError, KeyboardInterrupt):

        #     time_elapsed = time.time() - start_time
        #     logging.info("Measurement Completed! Time duration: %f", time_elapsed)
        # finally:
        #     self.stop()
        #     self._loop.close()
        pass

    async def stop(self):
        for _,ap in self._accesspoints.items():
            if not ap.connected:
                continue
            
            for phy in ap.phys:
                ap.writer.write(f"{phy};stop\n".encode("ascii"))
                ap.writer.write(f"{phy};auto\n".encode("ascii"))
                ap.writer.close()

        for task in self._tasks:
            print(f"Cancelling {task.get_name()}")
            task.cancel()

        if len(self._tasks) > 0:
            await asyncio.wait(self._tasks)

        if self._new_loop_created:
            self._loop.close()

        logging.info("RateMan stopped")

    def load_rc(self, rate_control_algorithm):
        entry_func = None

        if rate_control_algorithm == "minstrel_ht_user_space":
            try:
                from minstrel import start_minstrel
                entry_func = start_minstrel
            except ImportError:
                logging.error(f"Unable to execute user space minstrel: Import minstrel failed")

        return entry_func

    async def run(self):
        try:
            self._loop.run_forever()
        finally:
            await self.stop()

if __name__ == '__main__':

    def parse_aps(apstrs):
        aps = []

        for apstr in apstrs:
            fields = apstr.split(":")
            if len(fields) < 2:
                print(f"Invalid access point: '{apstr}'", file=sys.stderr)
                continue

            id = fields[0]
            addr = fields[1]

            try:
                rcd_port = int(fields[2])
            except (IndexError, ValueError):
                rcd_port = 21059

            aps.append(AccessPoint(id, addr, rcd_port))

        return aps

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
            "algorithm", type=str,
            choices=["minstrel_ht_kernel_space", "minstrel_ht_user_space"],
            default="minstrel_ht_kernel_space", 
            help="Rate control algorithm to run."
    )
    arg_parser.add_argument(
            "-A", "--ap-file", metavar="AP_FILE", type=str,
            help="Path to a csv file where each line contains information about an access point " +
            "in the format: ID,ADDR,RCDPORT."
    )
    arg_parser.add_argument(
            "accesspoints", metavar="AP", nargs="+", type=str,
            help="Accesspoint to connecto to. Format: 'ID:ADDR:RCDPORT'. " +
            "RCDPORT is optional and defaults to 21059."
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
    rateman = RateMan(aps, rate_control_alg=args.algorithm, loop=loop)

    # add a simple print callback to see the incoming data
    rateman.add_data_callback(lambda ap,line: print(f"{ap.id}> '{line}'"))

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman.stop())
        print("DONE")