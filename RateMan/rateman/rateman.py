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
                portID = int(currentAP["PORT"])
                SSHHost = currentAP["IPADD"]
                SSHPort = int(currentAP["SSHPORT"])
                SSHUsr = currentAP["SSHUSR"]
                SSHPass = currentAP["SSHPASS"]
                SSHConn = currentAP["SSH"]
                MinstrelRCD = currentAP["MRCD"]

                self._accesspoints[APID] = APID
                self._accesspoints[APID] = currentAP
                self._accesspoints[APID]["PORT"] = portID
                self._accesspoints[APID]["SSHPORT"] = SSHPort

                if SSHConn == "enable":
                    SSHClient = obtain_SSHClient(
                        SSHHost, SSHPort, SSHUsr, SSHPass)

                    phy_list = self._getPhyList(SSHClient)
                    wlan_list = self._getWLANList(SSHClient)

                    self._accesspoints[APID]["wlanList"] = wlan_list
                    self._accesspoints[APID]["phyList"] = phy_list
                    self._accesspoints[APID]["staList"] = {}
                    self._getStationList(SSHClient, wlan_list, APID)
                else:
                    self._accesspoints[APID]["wlanList"] = "not available"
                    self._accesspoints[APID]["phyList"] = "not available"
                    self._accesspoints[APID]["staList"] = "not available"

                if SSHConn == "enable" and MinstrelRCD == "off":
                    self._enableMinstrelRCD(SSHClient)
    
        pass
    

    def _getPhyList(self, SSHClient: object) -> list:
        """
        Get a list of the available radio devices for a given access point.

        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.

        Returns
        -------
        list
            List containing Phy ID strings.

        """

        command = "iw phy"

        stdin, stdout, stderr = SSHClient.exec_command(command)

        lines = stdout.readlines()

        phy_list = []
        for line in lines:
            if "Wiphy" in line:
                phy_list.append(line[6:-1])

        return phy_list

    def _getWLANList(self, SSHClient: object) -> list:
        """
        Get a list of the available WLAN devices for a given access point.
        Number of WLAN devices corresponds to the number of radios. 

        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.

        Returns
        -------
        list
            List containing WLAN device ID strings.

        """

        command = "iw dev"

        stdin, stdout, stderr = SSHClient.exec_command(command)

        lines = stdout.readlines()

        wlan_list = []
        for line in lines:
            if "Interface" in line:
                wlan_list.append(line[11:-1])

        return wlan_list

    def _getStationList(self, SSHClient: object, wlan_list: list, APID: str) -> None:
        """
        Get list of stations connected to a given WLAN device of the given
        access point.


        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.
        wlan_list : list
            List containing WLAN device ID strings.
        APID : str
            Access point ID.

        Returns
        -------
        None            

        """

        for wlan in wlan_list:
            station_list = []
            command = "iw dev " + wlan + " station dump"
            stdin, stdout, stderr = SSHClient.exec_command(command)
            lines = stdout.readlines()
            for line in lines:
                if "Station" in line:
                    station_list.append(line[8:25])
            self._accesspoints[APID]["staList"][wlan] = station_list

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

    def start(self) -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats).


        Returns
        -------
        None.

        """

        self._loop.create_task(main_AP_tasks(self._accesspoints, self._loop))

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            
        pass

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass
