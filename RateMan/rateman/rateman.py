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

    def add_raw_data_callback(self, cb):
        """
        Register a callback to be called on unvalidated incoming data
        """
        self._taskman.add_raw_data_callback(cb)

    def add_data_callback(self, cb, type="any"):
        """
        Register a callback to be called on validated incoming data.
        """
        self._taskman.add_data_callback(cb, type)

    def remove_data_callback(self, cb):
        """
        Unregister a data callback
        """
        self._taskman.remove_data_callback(cb)

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
