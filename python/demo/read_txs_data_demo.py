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
import nest_asyncio
import time
nest_asyncio.apply()



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

    #time.sleep(5)
    # add accesspoint 2
    accesspoint1Host = "10.10.200.2"
    accesspoint1Port = 21059

    rateMan.addaccesspoint(accesspoint1Host, accesspoint1Port)

    # stop ratemanager
    #time.sleep(10)
    print('make sure clients are present and wait for 5 seconds')
    rateMan.stop()
    ## Observe that 'txs' data files(.csv) are created








    # accesspointHandle = rateMan.accesspoints['AP1']['APHandle']
    
    # txsDataFrame = rateMan.read_txs(accesspointHandle, 1)
    
    ## loop processing
    # loop = asyncio.get_event_loop()
    # # loop.run_forever()
    
    
    # txsData2 = loop.create_task(conc.recv_linebyline_async())
    # txsData3 = loop.create_task(conc.recv_linebyline_async())
    
    # loop.stop()

    # # txsData1 = await conc.recv_linebyline_async()
        
    # # rr, ww = await asyncio.open_connection(accesspoint1Host, accesspoint1Port)
    
    # loop = asyncio.get_event_loop()
    
    # dC = ratemanager.DataCollector("10.10.200.2", 21059, loop)
    
    
    # # loop.run_forever()
    # loop.create_task(dC.test_func())
    # # dC._stop = False
    # txsData2 = dC.dataCollectorMain() #loop.create_task(dC.recv_linebyline_async())
    
    # dC._stop = True
    
    # loop.close()
  
    # loop = asyncio.get_event_loop()
    # thread = Thread(target=loop.run_forever)
    # thread.start()
    # print('Started!')
    # txsData2 = loop.create_task(dC.recv_linebyline_async()) #dC.dataCollectorMain() 
    # dC._stop = True
    # loop.call_soon_threadsafe(loop.stop)  # here
    # print('Requested stop!')
    # thread.join()
    # print('Finished!')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    