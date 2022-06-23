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
import csv
from datetime import datetime
import logging
import asyncio
import json
import os
from .accesspoint import AccessPoint
from .manage_asyncio import *
import time

__all__ = ["RateMan"]


class RateMan:
    def __init__(self, ap_list_dir: dir, 
                 rate_control_alg: str = 'minstrel_ht_kernel_space',
                 data_dir: dir = '') -> None:

        self._net_info = {}
        self._accesspoints = {}
        self._meas_info = ""

        try:
            self._loop = asyncio.get_running_loop()
        except:
            self._loop = asyncio.get_event_loop()
        
        self.add_ap_list(ap_list_dir, rate_control_alg)
        self.setup_tasks(data_dir)
        
    @property
    def clients(self) -> dict:
        # list of clients for a given AP at a given radio

        return 0

    @property
    def accesspoints(self) -> dict:
        # provides a list of access points in the network
        # dict with APID keys, with each key having a dict with radios,
        # which is also a dict with clients

        return self._accesspoints

    def add_ap_list(
        self, ap_list_dir: dir, rate_control_alg: str = "minstrel_ht_kernel_space"
    ) -> None:
        """
        Function to add a list of access points available in a network.
        Each access point has given a unique ID and relevant information
        is organized as a dict in the Rate Manager object as the
        the 'accesspoints' variable.

        Parameters
        ----------
        filename : dir

        Returns
        -------
        None

        """

        self._ap_list_dir = ap_list_dir
        with open(ap_list_dir, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for cur_AP in reader:

                AP_ID = cur_AP["APID"]
                AP_IP = cur_AP["IPADD"]
                AP_SSH_port = int(cur_AP["PORT"])
                AP_MinstrelRCD_port = 21059

                self._net_info[AP_ID] = AP_ID
                self._net_info[AP_ID] = cur_AP
                self._net_info[AP_ID]["SSHPORT"] = AP_SSH_port
                self._net_info[AP_ID]["MPORT"] = AP_MinstrelRCD_port

                AP_handle = AccessPoint(AP_ID, AP_IP, AP_SSH_port, AP_MinstrelRCD_port)
                AP_handle.rate_control_alg = rate_control_alg

                self._accesspoints[AP_ID] = AP_handle

        print("ap_list added")
        pass

    def setup_tasks(self, output_dir: str = "") -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats). Send notification about the experiment from RateMan
        Telegram Bot.

        Parameters
        ----------

        duration: float
            time duration for which the data from APs has to be collected

        output_dir : str
            directory to which parsed data is saved

        Returns
        -------
        None.

        """

        self._loop.create_task(setup_ap_tasks(self._accesspoints, output_dir))

        pass

    def start(self, output_dir: str = "") -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats). Send notification about the experiment from RateMan
        Telegram Bot.

        Parameters
        ----------

        duration: float
            time duration for which the data from APs has to be collected

        output_dir : str
            directory to which parsed data is saved

        Returns
        -------
        None.

        """

        start_time = time.time()
        try:
            self._loop.run_forever()
        except (OSError, KeyboardInterrupt):

            time_elapsed = time.time() - start_time
            logging.info("Measurement Completed! Time duration: %f", time_elapsed)
        finally:
            self.stop()
            self._loop.close()
        pass

    def stop(self):
        """
        This async function executes stop command in the APs (if indicated i.e.
        stop_cmd set to True). It also stops all the tasks and, finally, the
        event loop.

        Parameters
        ----------
        ap_handles : dictionary
            contains parameters such as ID, IP Address, Port, relevant file
            streams and connection status with each AP as key
        loop : event_loop
            DESCRIPTION.

        Returns
        -------
        None.

        """

        cmd_footer = ";stop"

        for APID in list(self._accesspoints.keys()):
            if self._accesspoints[APID].connection:
                writer = self._accesspoints[APID].writer
                for phy in self._accesspoints[APID].phy_list:
                    cmd = phy + cmd_footer
                    writer.write(cmd.encode("ascii") + b"\n")

                self._accesspoints[APID].file_handle.close()

        logging.info("RateMan stopped.")

    def stop_loop(self):

        for task in asyncio.all_tasks(self._loop):
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass
        self._loop.stop()
