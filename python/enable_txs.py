import connection
import pandas as pd
import io

def run_cmd(connectionObject, cmd):
    connectionObject.send(cmd.encode('ascii')+b'\n')

def start_radio(connectionObject, phy_id):
    cmd = phy_id + ';start'
    run_cmd(connectionObject, cmd)

def read_txs(connectionObject, time=3):
    txsData = connection.recv_with_timeout(connectionObject, timeout=time)
    txsDataFrame = pd.read_csv(io.StringIO(txsData), sep= ';')
    txsDataFrame.columns = ['radio','radioID','txs','macaddr','num_frames','num_acked','probe','rates','counts']

    return txsDataFrame

def main():
    HOST = "10.10.200.2"
    PORT = 21059
    apiStream = connection.open(HOST, PORT)
    data = connection.recv_end(apiStream, 'phy1;0;add\n')
    start_radio(apiStream, 'phy1')
    txsDataFrame = read_txs(apiStream, 5)
    print(txsDataFrame)
    apiStream.close()

if __name__ == '__main__':
    main()
