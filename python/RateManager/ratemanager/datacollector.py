# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Data Collector Object
----------------

This class provides an object for Data Collector which enables data collection
in an asynchronous fashion.

"""

import numpy as np
import socket
import time
import pdb
from io import BytesIO
import asyncio



__all__ = ["DataCollector"]


class DataCollector:
    @property
    def host(self) -> str:
        # list of clients for a given AP at a given radio
        
        return self._host
    
    @property
    def port(self) -> int:
        # list of clients for a given AP at a given radio
    
        return self._port
    
    
    def savedata(self, host: str, port:str) -> None:
        
        #data is structured per AP and can be structure per client
        
        pass             
    
    # create function for external data collection
    
    async def recv_linebyline_async(self):
        # TODO: asyncio connection object should be given a input parameter.
        print('dataCollector function called')
        outputData = []
        reader, writer = await asyncio.open_connection(
            self._host, self._port)

        randNum = np.random.randint(1,100)
        f = open('csvfile'+str(randNum)+'.csv','w')
    
        with BytesIO() as buffer:
    
            while True:
                #print('current time', time.time()-start_time)
                if self._stop is True:
                    f.close() 
                    break
                try:
                    resp = await reader.read(1024)
                except BlockingIOError:
                    #print("Sleeping")
                    await asyncio.sleep(2)
                else:
                    buffer.write(resp)
                    buffer.seek(0)
                    start_index = 0  # Count the number of characters processed
                    for line in buffer:
                        start_index += len(line)
                        #handle_line(line)       # Do something with your line
                        #print(line)
                        f.write(line.decode('utf-8'))
                        outputData.append(line)
    
                    """ If we received any newline-terminated lines, this will be nonzero.
                        In that case, we read the remaining bytes into memory, truncate
                        the BytesIO object, reset the file pointer and re-write the
                        remaining bytes back into it.  This will advance the file pointer
                        appropriately.  If start_index is zero, the buffer doesn't contain
                        any newline-terminated lines, so we set the file pointer to the
                        end of the file to not overwrite bytes.
                    """
                    if start_index:
                        buffer.seek(start_index)
                        remaining = buffer.read()
                        buffer.truncate(0)
                        buffer.seek(0)
                        buffer.write(remaining)
                    else:
                        buffer.seek(0, 2)         
        # f.close()        
        
        #return outputData
    
    def recv_linebyline_process(self, APHandle, APID):
        APHandle.setblocking(0)
        outputData = []
        #randNum = np.random.randint(1,100)
       
        # fileHandle = open('csvfile'+str(randNum)+'.csv','w')
        fileHandle = open('txsData_'+APID+'.csv','w')
        print('TX Status Data file created for', APID)
        
        with BytesIO() as buffer:
    
            while True:
                if self._stop is True:
                    fileHandle.close() 
                    break
                try:
                    resp = APHandle.recv(1024)
                except BlockingIOError:
                    print("Sleeping")
                    time.sleep(2)
                else:
                    buffer.write(resp)
                    buffer.seek(0)
                    start_index = 0  # Count the number of characters processed
                    for line in buffer:
                        start_index += len(line)
                        # handle_line(line)       # Do something with your line
                        fileHandle.write(line.decode('utf-8'))
                        outputData.append(line)
                        
    
                    """ If we received any newline-terminated lines, this will be nonzero.
                        In that case, we read the remaining bytes into memory, truncate
                        the BytesIO object, reset the file pointer and re-write the
                        remaining bytes back into it.  This will advance the file pointer
                        appropriately.  If start_index is zero, the buffer doesn't contain
                        any newline-terminated lines, so we set the file pointer to the
                        end of the file to not overwrite bytes.
                    """
                    if start_index:
                        buffer.seek(start_index)
                        remaining = buffer.read()
                        buffer.truncate(0)
                        buffer.seek(0)
                        buffer.write(remaining)
                    else:
                        buffer.seek(0, 2)
                        
            # return outputData         
    

    def __init__(self, host, port) -> None:
        # 
        self._host = host
        self._port = port        
        self._stop = False
        
