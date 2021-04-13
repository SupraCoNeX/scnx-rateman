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

import numpy as np
from connection import *
import pandas as pd
import io
import time
import paramiko


#from . import __version__


__all__ = ["RateManager"]


class RateManager:
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
    

    def addaccesspoint(self, host: str, port: int) -> None:
        
        #open connection
        numAccessPoints = len(self.accesspoints)
        newAccessPointID = 'AP'+str(numAccessPoints+1)
        
        accesspoint = {}
        
        accesspointHandle = openconnection(host, port)
        
        accesspoint['APHandle'] = accesspointHandle
        
        #create initial data stream for new AP
        txsDataFrame = self._read_txs(accesspointHandle, 1)

        #create list of radios
        columnOfRadios = txsDataFrame['*'].values
        radios = columnOfRadios[columnOfRadios != '*']
        
        accesspoint['radios'] = radios
        
        #update rate manager AP list
        self._accesspoints[newAccessPointID] = accesspoint
              
        #enable radios, all by default
        for radioID in radios:
            self._start_radio(accesspointHandle, radioID)
        
        #collect tx status data        
        print('add clients')
        txsDataFrame = self._read_txs(accesspointHandle, 10)
                
        self._accesspoints[newAccessPointID]['txsData'] = txsDataFrame
        
        #ToDo clients = client list from txs data
        
        #ToDo self._accesspoints[newAccessPointID]['clients'] = clients
        
        #collect rc_stats data
        sshClient = 0
        localPath = '0'
        remotePath = '0'
        
        self._rcstats = self._get_rcstats(sshClient, localPath, remotePath)
        
        #ToDo rc_stats = list of available
        
    def setrate(self, accesspointID, radioID, clientID, rateIndexHex) -> None:
        
        #set the given rate for the given client
        APHandle = self._accesspoints['accesspointID']['APHandle']
        
        cmd = radioID + ';rates;' + clientID + ';' + rateIndexHex +';1'
        #'phy1;rates;' + macaddr + ';' + rateIndexHex +';1'
        self._run_cmd(APHandle, cmd)
        
    def savedata(self, host: str, port:str) -> None:
        
        #data is structured per AP and can be structure per client
        
        pass
    
    def removeaccesspoint(self, host: str, port:str) -> None:
        
        pass
    
    def _run_cmd(self, accesspointHandle, cmd):
        accesspointHandle.send(cmd.encode('ascii')+b'\n')
        
    def _start_radio(self, accesspointHandle, phy_id) -> None:
        cmd = phy_id + ';start'
        self.run_cmd(accesspointHandle, cmd)
        
        
    def _get_rcstats(self, ssh: paramiko.client.SSHClient,
            localpath: str, remotepath: str) -> None:
        sftp = ssh.open_sftp()
        sftp.put(localpath, remotepath)
        sftp.close()
        
        return sftp
        
    def _read_txs(self, accesspointHandle, until_time=3):
        txsData = recv_until_time(accesspointHandle, until_time)
        txsDataFrame = pd.read_csv(io.StringIO(txsData), sep= ';')
        #txsDataFrame.columns = ['radio','timestamp','txs','macaddr','num_frames','num_acked','probe','rates','counts']

        return txsDataFrame
    
    # create function for external data collection

    def __init__(self) -> None:
        
        self._accesspoints = {}
        self._txsDataFrame = []
        self._rcstats = []
        
