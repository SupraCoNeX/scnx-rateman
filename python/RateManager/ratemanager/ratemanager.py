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
        accesspoint = openconnection(host, port)
        
        #update rate manager AP list
        self._accesspoints[newAccessPointID] = accesspoint
        
        #create data stream for new AP
        
        #create list of radios
        
        #enable radios, all by default
        
        #collect tx status data
        
        #collect rc_stats data
        
        pass  
    
    def setrate(self, accesspointID, radioID, clientID, rateIndex):
        
        #set the given rate for the given client
        
        pass

    def savedata(self, host: str, port:str) -> None:
        
        #data is structured per AP and can be structure per client
        
        pass
    
    def removeaccesspoint(self, host: str, port:str) -> None:
        
        pass
    
    def run_cmd(self, connectionObject, cmd):
        connectionObject.send(cmd.encode('ascii')+b'\n')
        
    def start_radio(self, connectionObject, phy_id) -> None:
        cmd = phy_id + ';start'
        self.run_cmd(connectionObject, cmd)
        
    def read_txs(connectionObject, until_time=3):
        txsData = connection.recv_until_time(connectionObject, until_time)
        txsDataFrame = pd.read_csv(io.StringIO(txsData), sep= ';')
        #txsDataFrame.columns = ['radio','timestamp','txs','macaddr','num_frames','num_acked','probe','rates','counts']

        return txsDataFrame

    def __init__(self) -> None:
        
        self._accesspoints = {}
