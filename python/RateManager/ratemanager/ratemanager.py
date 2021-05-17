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
import pandas as pd
import dask as da
import io
import time
import paramiko
from .datahandler import DataHandler
import asyncio
import multiprocessing as mp


__all__ = ["RateManager"]


class RateManager:
    def __init__(self) -> None:

        self._accesspoints = {}
        self._txsDataFrame = []
        self._rcstats = []

        self._loop = asyncio.get_event_loop()
        # self._loop.run_until_complete()
        # self._tasks = []

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
                
                
                if APID == 'AP1':
                    SSHClient = paramiko.SSHClient()
                    SSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    SSHClient.connect(SSHHost, SSHPort, SSHUsr, SSHPass)

                    SSHClient.exec_command("minstrel-rcd -h 0.0.0.0 &")
                    
                APHandle = openconnection(IPAdd, portID)

                self._accesspoints[APID]['APHandle'] = APHandle
                
                radios = ['phy0', 'phy1']
                self._accesspoints[APID]['radios'] = radios

                for radioID in radios:
                    self._start_radio(APHandle, radioID)              

                dataHandle = DataHandler(APHandle, APID)

                self._accesspoints[APID]['DataHandle'] = dataHandle

                dataProcess = mp.Process(
                    name="txsDataProcess",
                    target=dataHandle.recv_linebyline_process,
                    args=(),
                )
                
                self._accesspoints[APID]['dataProcess'] = dataProcess

        # create initial data stream for new AP
        # txsDataFrame = dataHandle.recv_until_time(1)

        # # create list of radios
        # if type(txsDataFrame) not list:
        #     columnOfRadios = txsDataFrame["*"].values
        # radios = columnOfRadios[columnOfRadios != "*"]
        # radios = ['phy0', 'phy1']

        # accesspoint["radios"] = radios
       
        # # enable radios, all by default
        # for radioID in radios:
        #     self._start_radio(accesspointHandle, radioID)

        # Create data collection object

        

        # ToDo clients = client list from txs data

        # ToDo self._accesspoints[newAccessPointID]['clients'] = clients

        # collect rc_stats data
        # sshClient = 0
        # localPath = '0'
        # remotePath = '0'

        # self._rcstats = self._get_rcstats(sshClient, localPath, remotePath)

        # ToDo rc_stats = list of available

    def start_monitoring(self, until_time=10):
        
        # obtain list of APs
        APIDs = list(self._accesspoints.keys())
        for APID in APIDs:
            dataProcesstemp = self._accesspoints[APID]["dataProcess"]
            dataProcesstemp.start()
        
        
        
    def setrate(self, accesspointID, radioID, clientID, rateIndexHex) -> None:

        # set the given rate for the given client
        APHandle = self._accesspoints["accesspointID"]["APHandle"]

        cmd = radioID + ";rates;" + clientID + ";" + rateIndexHex + ";1"
        #'phy1;rates;' + macaddr + ';' + rateIndexHex +';1'
        self._run_cmd(APHandle, cmd)

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass

    def removeaccesspoint(self, host: str, port: str) -> None:

        pass

    def _run_cmd(self, accesspointHandle, cmd):
        accesspointHandle.send(cmd.encode("ascii") + b"\n")

    def _start_radio(self, accesspointHandle, phy_id) -> None:
        cmd = phy_id + ";start;stats;txs"
        self._run_cmd(accesspointHandle, cmd)

    def _get_rcstats(
        self, ssh: paramiko.client.SSHClient, localpath: str, remotepath: str
    ) -> None:
        sftp = ssh.open_sftp()
        sftp.put(localpath, remotepath)
        sftp.close()

        return sftp

    def read_txs(self, accesspointHandle, until_time=3):
        """
        Under development - do not use.

        Parameters
        ----------
        accesspointHandle : TYPE
            DESCRIPTION.
        until_time : TYPE, optional
            DESCRIPTION. The default is 3.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        return self._read_txs(accesspointHandle, until_time)

    def _stop(self) -> None:
        self._stop = True
        for AP in list(self._accesspoints.keys()):
            dataHandlerTemp = self._accesspoints[AP]["DataHandle"]
            dataHandlerTemp._stop = True
            dataProcess = self._accesspoints[AP]["dataProcess"]
            dataProcess.terminate()

    def stop(self) -> None:
        self._stop()
