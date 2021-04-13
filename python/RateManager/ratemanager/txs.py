#from api_controller import *
from api_controller import *
import connection
import pandas as pd
import io


def read_txs(connectionObject, until_time=3):
    txsData = connection.recv_until_time(connectionObject, until_time)
    txsDataFrame = pd.read_csv(io.StringIO(txsData), sep= ';')
    #txsDataFrame.columns = ['radio','timestamp','txs','macaddr','num_frames','num_acked','probe','rates','counts']

    return txsDataFrame

def main():
    HOST = "10.10.200.2"
    PORT = 21059
    apiStream = connection.open(HOST, PORT)
    data = connection.recv_end(apiStream, 'phy1;0;add\n')
    start_radio(apiStream, 'phy1')
    start_radio(apiStream, 'phy0')
    txsDataFrame = read_txs(apiStream, 5)
    print(txsDataFrame)
    apiStream.close()

if __name__ == '__main__':
    main()
