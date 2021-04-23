# test
import connection
import dask as da
import dask.dataframe as dd
import io
import pandas as pd
import time
import numpy as np
import paramiko
from scp import SCPClient

if __name__ == '__main__':

    #add accesspoint
    accesspoint1Host = "10.10.200.2"
    accesspoint1Port = 21059
    
    accesspointHandle = connection.openconnection(accesspoint1Host,
                                                  accesspoint1Port)

    # enable minstrel-rcd

    ssh1Host = "10.10.200.2"
    ssh1Port = 22
    ssh1Username = "root"
    ssh1Password = "sommer4"

    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.connect(ssh1Host, ssh1Port, ssh1Username, ssh1Password)

    command = "minstrel-rcd -h 0.0.0.0 &"
    
    macaddr = 'f8:16:54:6a:13:69'
   
    # sftp_client = ssh1.open_sftp()
    
    # ssh2 = paramiko.Transport((ssh1Host, 22))  
    # ssh2.connect(username=ssh1Username, password=ssh1Password) 
    # sftp_client = paramiko.SFTPClient.from_transport(ssh2)
    
    
    filename = '/sys/kernel/debug/ieee80211/phy1/netdev:wlan1/stations/f8:16:54:6a:13:69/rc_stats_csv'
    
    
    ssh1.exec_command('cp ' + filename + ' /tmp/')
    
    
    scpClient1 = SCPClient(ssh1.get_transport())
    
    scpClient1.get('/tmp/rc_stats_csv', 'rc_stats_csv4')
    
       
    
    