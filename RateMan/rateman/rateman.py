#!/usr/bin/python3
# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import argparse
import sys
import logging
import asyncio
from .accesspoint import AccessPoint
from .tasks import TaskMan
from .parsing import *



__all__ = ["RateMan"]


class RateMan:
    def __init__(
        self, aps, rate_control_alg: str = "minstrel_ht_kernel_space", 
        loop=None, output_dir=None):
        if not loop:
            logging.info("Creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._new_loop_created = True
        else:
            self._new_loop_created = False

        self._accesspoints = {}        
        self._taskman = TaskMan(loop)
        
        for ap in aps:
            ap.rate_control_alg = rate_control_alg
            ap.rate_control = self.load_rc(rate_control_alg)
            self._accesspoints[ap.id] = ap
            self._taskman.add_task(self._taskman.connect_ap(ap, 5), name=f"connect_{ap.id}")

    @property
    def taskman(self) -> dict:
        return self._taskman
    
    @property
    def accesspoints(self) -> dict:
        return self._accesspoints

    async def stop(self):
        for _, ap in self._accesspoints.items():
            if not ap.connected:
                continue

            for phy in ap.phys:
                ap.writer.write(f"{phy};stop\n".encode("ascii"))
                ap.writer.write(f"{phy};auto\n".encode("ascii"))
                ap.writer.close()

        for task in self._taskman.tasks:
            logging.info(f"Cancelling {task.get_name()}")
            task.cancel()

        if len(self._taskman.tasks) > 0:
            await asyncio.wait(self._taskman.tasks)

        if self._new_loop_created:
            self._taskman.cur_loop.close()

        logging.info("RateMan stopped")

    def load_rc(self, rate_control_algorithm):
        entry_func = None

        if rate_control_algorithm == "minstrel_ht_user_space":
            try:
                from minstrel import start_minstrel

                entry_func = start_minstrel
            except ImportError:
                logging.error(
                    f"Unable to execute user space minstrel: Import {rate_control_algorithm} failed"
                )

        return entry_func

if __name__ == "__main__":

    def parse_aps(apstrs):
        aps = []

        for apstr in apstrs:
            fields = apstr.split(":")
            if len(fields) < 2:
                print(f"Invalid access point: '{apstr}'", file=sys.stderr)
                continue

            ap_id = fields[0]
            addr = fields[1]

            try:
                rcd_port = int(fields[2])
            except (IndexError, ValueError):
                rcd_port = 21059

            aps.append(AccessPoint(ap_id, addr, rcd_port))

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
        + "in the format: ID,ADDR,RCDPORT.",
    )
    arg_parser.add_argument(
        "accesspoints",
        metavar="AP",
        nargs="*",
        type=str,
        help="Accesspoint to connecto to. Format: 'ID:ADDR:RCDPORT'. "
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
    rateman = RateMan(aps, rate_control_alg=args.algorithm, loop=loop)

    # add a simple print callback to see the incoming data
    rateman.add_data_callback(lambda ap, line: print(f"{ap.id}> '{line}'"))

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rateman.stop())
        print("DONE")

