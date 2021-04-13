from  api_controller import run_cmd, HOST, PORT
import connection
import txs

def set_rate(connectionObject, macaddr, rateIndexHex):
    cmd = 'rates;' + macaddr + ';' + rateIndexHex +';1' #'rates;macaddr;rates;counts'
    run_cmd(connectionObject, cmd)

def main():
    connectionObject = connection.open(HOST, PORT)
    cmd = 'phy1' + ';start'
    run_cmd(connectionObject, cmd)
    cmd = 'phy1' + ';stop'
    run_cmd(connectionObject, cmd)
    macaddr = 'f8'
    rateIndexHex = 'd5'
    set_rate(connectionObject, macaddr, rateIndexHex)

if __name__ == '__main__':
    main()
