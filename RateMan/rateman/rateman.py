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
import asyncio
import json
import os
from .accesspoint import AccessPoint
from .manage_asyncio import *

__all__ = ["RateMan"]


class RateMan:
    def __init__(self) -> None:

        self._net_info = {}
        self._ap_handles = {}
        self._accesspoints = {}
        self._meas_info = ""

        self._loop = asyncio.get_event_loop()

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

    def add_ap_list(self, ap_list_filename: dir, rate_control_info: dict = {}) -> None:
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

        self._ap_list_filename = ap_list_filename
        with open(ap_list_filename, newline="") as csvfile:
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

                if rate_control_info[AP_ID]["rc_type"] == "active":
                    AP_handle.rate_control_type = "active"
                    AP_handle.rate_control_alg = rate_control_info[AP_ID]["rc_alg"]
                    AP_handle.rate_control_settings = rate_control_info[AP_ID][
                        "param_settings"
                    ]
                else:
                    AP_handle.rate_control_type = "passive"
                    AP_handle.rate_control_alg = "kernel-minstrel-ht"

                self._ap_handles[AP_ID] = AP_handle

        pass

    def start(self, duration: float, output_dir: str = "") -> None:
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

        self._duration = duration

        self._loop.create_task(setup_ap_tasks(self._ap_handles, duration, output_dir))
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
        pass
