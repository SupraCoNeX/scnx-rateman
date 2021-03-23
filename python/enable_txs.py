import telnet_py

def run_cmd(tn, cmd):
    tn.write(cmd.encode('ascii')+b'\n')

def enable_txs(tn, phy_id):
    cmd = phy_id + ';start'
    run_cmd(tn, cmd)

def read_txs(tn, time=3):
    bdata = tn.read_until(b'dhfjhfkdsfhf', timeout=time)
    data = bdata.decode('utf-8')
    #TODO: parse tx data and put in DataFrame(pandas)
    return data

def main():
    tn = telnet_py.open(telnet_py.HOST, telnet_py.PORT)
    enable_txs(tn, 'phy1')
    tx_data = read_txs(tn)
    print(tx_data)
    tn.close()

if __name__ == '__main__':
    main()
