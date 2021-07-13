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
import numpy as np
from .connman import *
from .core import *
import io
import time
import paramiko
import asyncio


__all__ = ["RateMan"]


class RateMan:
    def __init__(self) -> None:

        self._accesspoints = {}
        self._txsDataFrame = []
        self._rcstats = []

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

    def addaccesspoints(self, filename: dir) -> None:
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
        with open(filename, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for currentAP in reader:

                APID = currentAP["APID"]
                IPAdd = currentAP["IPADD"]
                portSSH = int(currentAP["PORT"])
                portMinstrel = 21059  # default port for Minstrel-RCD

                self._accesspoints[APID] = APID
                self._accesspoints[APID] = currentAP
                self._accesspoints[APID]["PORT"] = portSSH
                self._accesspoints[APID]["MPORT"] = portMinstrel

                # phy list is hard-coded -> ToDo: obtain list automatically
                # using getPhyList function
                self._accesspoints[APID]["phyList"] = ["phy0", "phy1"]

        pass

    def _enableMinstrelRCD(self, SSHClient: object) -> None:
        """


        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.

        Returns
        -------
        None
            DESCRIPTION.

        """

        cmd = "minstrel-rcd -h 0.0.0.0 &"
        execute_command_SSH(SSHClient, cmd)

        pass

    def start(self, duration: float, output_dir: str = '') -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats).


        Returns
        -------
        None.

        """
        
        self._loop.create_task(
            main_AP_tasks(self._accesspoints, self._loop, duration, output_dir)
        )

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

        pass

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass
