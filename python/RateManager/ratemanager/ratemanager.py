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
from .connection import *
from .async_control import *
import io
import time
import paramiko
import asyncio


__all__ = ["RateManager"]


class RateManager:
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
        Function to add a given access point to the network. Each access point
        is given a unique ID and relevant information is organized as a dict
        in the Rate Manager object in the 'accesspoints' variable.

        Parameters
        ----------
        host : str
            Host ID of the access point.
        port : int
            Port of the access point.

        Returns
        -------
        None

        """

        # load file data

        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for currentAP in reader:

                APID = currentAP['APID']
                IPAdd = currentAP['IPADD']
                portID = int(currentAP['PORT'])
                SSHHost = currentAP['SSHHOST']
                SSHPort = int(currentAP['SSHPORT'])
                SSHUsr = currentAP['SSHUSR']
                SSHPass = currentAP['SSHPASS']

                self._accesspoints[APID] = APID
                self._accesspoints[APID] = currentAP
                self._accesspoints[APID]['PORT'] = portID
                self._accesspoints[APID]['SSHPORT'] = SSHPort

                # if APID == 'AP1':
                #     SSHClient = paramiko.SSHClient()
                #     SSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                #     SSHClient.connect(SSHHost, SSHPort, SSHUsr, SSHPass)

                #     SSHClient.exec_command("minstrel-rcd -h 0.0.0.0 &")

                # APHandle = openconnection(IPAdd, portID)


    def start(self) -> None:
        """
        Start RateMan

        Returns
        -------
        None.

        """
        
        self._loop.create_task(main_AP_tasks(self._accesspoints, self._loop))
        
        try:
            self._loop.run_forever()  # runs until loop.stop() is triggered
        finally:
            self._loop.close()

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass
 
