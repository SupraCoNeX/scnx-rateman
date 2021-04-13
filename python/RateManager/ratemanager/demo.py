# -*- coding: utf-8 -*-

# import connection
# import txs
from ratemanager import RateManager
import paramiko


if __name__ == '__main__':

    #enable minstrel-rcd
    
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
    rateMan = RateManager()
    
    # add accesspoint
    accesspoint1Host = "10.10.200.2"
    accesspoint1Port = 21059
    
    rateMan.addaccesspoint(accesspoint1Host, accesspoint1Port)
    
    # collect data

    # apiStream = connection.open(HOST, PORT)
    
    
    #data = connection.recv_end(apiStream, 'phy1;0;add\n')
    #start_radio(apiStream, 'phy1')
    #start_radio(apiStream, 'phy0')
    # txsDataFrame = txs.read_txs(apiStream, 1)
    #print(txsDataFrame)
    # run_cmd(apiStream, 'phy1;stop')
    # run_cmd(apiStream, 'phy1;manual')
    # macaddr = 'f8:16:54:6a:13:69'
    # rateIndexHex = 'd5'
    #set_rate(apiStream, macaddr, rateIndexHex)
    # cmd = 'phy1;rates;' + macaddr + ';' + rateIndexHex +';1'
    # run_cmd(apiStream, cmd)   
    #txsDataFrame.to_csv('out.zip',index=False)
    #apiStream.close()

