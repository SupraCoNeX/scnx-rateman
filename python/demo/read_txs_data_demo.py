# -*- coding: utf-8 -*-
"""
Created on Fri Apr 23 11:48:22 2021

@author: pawarsp
"""

import ratemanager 
import paramiko
import ratemanager.connection as conc
import asyncio
from threading import Thread
#import nest_asyncio
import time
#nest_asyncio.apply()



if __name__ == '__main__':
    # enable minstrel-rcd

    ssh1Host = "10.10.200.2"
    ssh1Port = 22
    ssh1Username = "root"
    ssh1Password = "sommer4"

    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.connect(ssh1Host, ssh1Port, ssh1Username, ssh1Password)

    command = "minstrel-rcd -h 0.0.0.0 &"
    ssh1.exec_command(command)

    # Create rateman object
    rateMan = ratemanager.RateManager()

    # add accesspoint 1
    accesspoint1Host = "10.10.200.2"
    accesspoint1Port = 21059

    rateMan.addaccesspoint(accesspoint1Host, accesspoint1Port)

    time.sleep(2)
    # add accesspoint 2
    accesspoint1Host = "10.10.200.2"
    accesspoint1Port = 21059

    rateMan.addaccesspoint(accesspoint1Host, accesspoint1Port)

    # stop ratemanager
    time.sleep(5)
    
    print('make sure clients are present and wait for 5 seconds')
    
    time.sleep(5)
    rateMan.stop()

    print('Observe that txs data files(.csv) are created')


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    