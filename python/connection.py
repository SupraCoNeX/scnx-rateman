import socket
import time
import pdb

HOST = "1.2.3.4"
PORT = 12345

def open(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s

def close(s):
    s.close()

# From: https://code.activestate.com/recipes/408859/
def recv_basic(s):
    """Read data from socket until socket disconnects."""
    s.setblocking(0)
    all_data = []
    while True:
        data = s.recv(8192)
        print(repr(data))
        pdb.set_trace()
        if not data:
            break
        all_data.append(data)
    return ''.join(all_data)

# More infos about blocking and non-blocking sockets:
# https://code.activestate.com/recipes/408859/
def recv_with_timeout(s, timeout=2):
    s.setblocking(0)
    total_data = []
    data = ''
    begin = time.time()
    while True:
        if total_data and time.time()-begin>timeout:
            break
        elif time.time()-begin>timeout*2:
            break
        try:
            data = s.recv(8192).decode('utf-8')
            if data:
                total_data.append(data)
                begin = time.time()
            else:
                time.sleep(0.1)
        except:
            pass
    return ''.join(total_data)

def recv_end(s, end_marker):
    """Read until end_marker."""
    #TODO: combine with timeout
    total_data = []
    data = ''
    while True:
        data = s.recv(8192).decode('utf-8')
        lm = len(end_marker)
        if end_marker in data:
            total_data.append(data[:data.find(end_marker)+lm])
            break
        total_data.append(data)
        if len(total_data)>1:
            # Check if end_of_data was split
            last_pair = total_data[-2] + total_data[-1]
            if end_marker in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_marker)]
                total_data.pop()
                break
    return ''.join(total_data)

def main():
    s = open(HOST, PORT)
    #data = recv_with_timeout(s)
    end_marker = 'phy1;0;add\n'
    data = recv_end(s, end_marker)
    s.close()

if __name__ == "__main__":
    main()
