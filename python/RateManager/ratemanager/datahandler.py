# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Data Handler Object
----------------

This class provides an object for Data Handler which enables data collection
in an asynchronous fashion.

"""

import socket
import time
import pdb
import io 
import asyncio
from pathlib import Path

import numpy as np
import pandas as pd


__all__ = ["DataHandler"]


class DataHandler:
    def __init__(self, APHandle, APID) -> None:              
        self._host = APHandle.getpeername()[0]
        self._port = APHandle.getpeername()[1]
        self._APHandle = APHandle
        self._APID = APID
        self._stop = False
        

    @property
    def host(self) -> str:
        # list of clients for a given AP at a given radio

        return self._host

    @property
    def port(self) -> int:
        # list of clients for a given AP at a given radio

        return self._port

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass

    def read_stats_txs_csv(self, filename: str) -> pd.core.frame.DataFrame:
        """Read rc_stats and tx status from the given csv file.

        Parameters:
        -----------
        filename : str
            Path plus filename of csv file containing the tx-status data.
        
        Returns:
        --------
        txs_data : pd.core.frame.DataFrame
            Pandas dataframe with tx status of the client.
        stats_data : pd.core.frame.DataFrame
            Pandas datafram with rc_stats data of the client.
        """
        p = Path(filename)
        if not p.exists():
            raise FileNotFoundError
        else:
            # Read CSV file containing tx status and rc_stats and save in
            # dataframe `df`.
            df = pd.read_csv(p, sep=';', header=3)
            # Filter tx status from dataframe `df`.
            txs_data = df[df.iloc[:,2] == 'txs'].iloc[:,:9]
            txs_data.columns = [
                'phy_nr',
                'timestamp',
                'type',
                'macaddr',
                'num_frames',
                'num_acked',
                'probe',
                'rates',
                'counts'
            ]
            # Filter rc_stats from dataframe `df`.
            stats_data = df[df.iloc[:,2] == 'stats']
            stats_data.columns = [
                'phy_nr',
                'timestamp',
                'type',
                'macaddr',
                'rate',
                'avg_prob',
                'avg_tp',
                'cur_success',
                'cur_attempts',
                'hist_success',
                'hist_attempts'
            ]
            # Set timestamps as index for both dataframes `txs_data` and
            # `stats_data`.
            txs_data.set_index('timestamp')
            stats_data.set_index('timestamp')
        return txs_data, stats_data

    
    def recv_linebyline_process(self):
        self._APHandle.setblocking(0)
        outputData = []
        fileHandle = open("txsData_" + self._APID + ".csv", "w")
        print("TX Status Data file created for", self._APID)

        with io.BytesIO() as buffer:

            while True:
                if self._stop is True:
                    fileHandle.close()
                    break
                try:
                    resp =  self._APHandle.recv(1024)
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
                        fileHandle.write(line.decode("utf-8"))
                        outputData.append(line)

                    """ If we received any newline-terminated lines, this will be nonzero.
                        In that case, we read the remaining bytes into memory, truncate
                        the io.BytesIO object, reset the file pointer and re-write the
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
                      
    
    async def recv_linebyline_async(self):
        # TODO: asyncio connection object should be given a input parameter.
        print("dataCollector function called")
        outputData = []
        reader, writer = await asyncio.open_connection(self._host, self._port)

        randNum = np.random.randint(1, 100)
        f = open("csvfile" + str(randNum) + ".csv", "w")

        with io.BytesIO() as buffer:
            try:
                while True:
                    # print('current time', time.time()-start_time)
                    try:
                        resp = await reader.read(1024)
                    except BlockingIOError:
                        # print("Sleeping")
                        await asyncio.sleep(2)
                    else:
                        buffer.write(resp)
                        buffer.seek(0)
                        start_index = 0  # Count the number of characters processed
                        for line in buffer:
                            start_index += len(line)
                            # handle_line(line)       # Do something with your line
                            # print(line)
                            f.write(line.decode("utf-8"))
                            outputData.append(line)                            
                        if start_index:
                            """ If we received any newline-terminated lines, this will be nonzero.
                                In that case, we read the remaining bytes into memory, truncate
                                the io.BytesIO object, reset the file pointer and re-write the
                                remaining bytes back into it.  This will advance the file pointer
                                appropriately.  If start_index is zero, the buffer doesn't contain
                                any newline-terminated lines, so we set the file pointer to the
                                end of the file to not overwrite bytes.
                            """
                            buffer.seek(start_index)
                            remaining = buffer.read()
                            buffer.truncate(0)
                            buffer.seek(0)
                            buffer.write(remaining)
                        else:
                            buffer.seek(0, 2)
                            
            except self._stop is True:
                f.close()
        # f.close()

        # return outputData
    
    def start_process(self):
        
        
        pass
    
    

    # From: https://code.activestate.com/recipes/408859/
    def recv_basic(self, socketHandle):
        """Read data from socket until socket disconnects."""
        socketHandle.setblocking(0)
        all_data = []
        while True:
            data = socketHandle.recv(8192)
            print(repr(data))
            pdb.set_trace()
            if not data:
                break
            all_data.append(data)
        return "".join(all_data)

    # More infos about blocking and non-blocking sockets:
    # https://code.activestate.com/recipes/408859/
    def recv_with_timeout(self, timeout=2):
        self._APHandle.setblocking(0)
        total_data = []
        data = ""
        begin = time.time()
        while True:
            if total_data and time.time() - begin > timeout:
                break
            elif time.time() - begin > timeout * 2:
                break
            try:
                data =  self._APHandle.recv(8192).decode("utf-8")
                if data:
                    total_data.append(data)
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return "".join(total_data)

    def recv_until_time(self, until_time=2):
        """
        
        Parameters
        ----------
        until_time : int, optional
            Time for which data is to be received.

        Returns
        -------
        dataFrame : Pandas Data Frame 
            Data frame that structures comma separated data of 
            string data type.

        """
        
        
        self._APHandle.setblocking(0)
        total_data = []
        data = ""
        begin = time.time()
        while True:
            if total_data and time.time() - begin > until_time:
                break
            elif time.time() - begin > until_time * 2:
                break
            try:
                data =  self._APHandle.recv(8192).decode("utf-8")
                if data:
                    total_data.append(data)
                    # begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        dataStr = "".join(total_data)
        try:
            dataFrame = pd.read_csv(io.StringIO(dataStr), sep=";")
        except:
            dataFrame = []
        # txsDataFrame = da.dataframe.read_csv(io.StringIO(txsData), sep= ';')
        # txsDataFrame.columns = ['radio','timestamp','txs','macaddr','num_frames','num_acked','probe','rates','counts']
         
        return dataFrame
    

    def recv_end(self, end_marker):
        """Read until end_marker."""
        # TODO: combine with timeout
        total_data = []
        data = ""
        while True:
            data =  self._APHandle.recv(8192).decode("utf-8")
            lm = len(end_marker)
            if end_marker in data:
                total_data.append(data[: data.find(end_marker) + lm])
                break
            total_data.append(data)
            if len(total_data) > 1:
                # Check if end_of_data was split
                last_pair = total_data[-2] + total_data[-1]
                if end_marker in last_pair:
                    total_data[-2] = last_pair[: last_pair.find(end_marker)]
                    total_data.pop()
                    break
        return "".join(total_data)

    # From: https://stackoverflow.com/a/29024384

    def recv_linebyline(self, timeout=15):
        self._APHandle.setblocking(0)
        begin = time.time()
        outputData = []

        with io.BytesIO() as buffer:
            start_time = time.time()

            while True:
                print("current time", time.time() - start_time)
                if time.time() - begin > timeout:
                    break
                try:
                    resp =  self._APHandle.recv(1024)
                except BlockingIOError:
                    print("Sleeping")
                    time.sleep(2)
                else:
                    begin = time.time()
                    buffer.write(resp)
                    buffer.seek(0)
                    start_index = 0  # Count the number of characters processed
                    for line in buffer:
                        start_index += len(line)
                        self._handle_line(line)  # Do something with your line
                        outputData.append(line)

                    """ If we received any newline-terminated lines, this will be nonzero.
                        In that case, we read the remaining bytes into memory, truncate
                        the io.BytesIO object, reset the file pointer and re-write the
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

        return outputData

    def _handle_line(self, line):
        line_str = line.decode("utf-8")
        if "sta;add" in line_str:
            print("Station added")
            indexStr = line_str.find("sta;add")
            print("macaddr:", line_str[indexStr + 10 : indexStr + 20])
        elif "txs;" in line_str:
            print("Station present")
            indexStr = line_str.find("sta;add") + 4
            print("macaddr:", line_str[indexStr : indexStr + 17])
        elif "txs;macaddr" in line_str:
            print("Basic TX status")

        # elif sta; remove:
        #     ...
        # elif tx:
        #     ...
        # else:
        #     ...
        pass
