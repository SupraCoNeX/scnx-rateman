import socket
import time
import pdb
from io import BytesIO

HOST = "10.10.200.2"
PORT = 21059

__all__ = [
    "openconnection",
    "closeconnection",
    "recv_basic",
    "recv_with_timeout",
    "recv_until_time",
    "recv_end",
    "recv_linebyline"
]

def openconnection(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s

def closeconnection(s):
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

def recv_until_time(s, until_time=2):
    s.setblocking(0)
    total_data = []
    data = ''
    begin = time.time()
    while True:
        if total_data and time.time()-begin>until_time:
            break
        elif time.time()-begin>until_time*2:
            break
        try:
            data = s.recv(8192).decode('utf-8')
            if data:
                total_data.append(data)
                # begin = time.time()
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

#From: https://stackoverflow.com/a/29024384                  
                    
def recv_linebyline(s, timeout=15):
    s.setblocking(0)
    begin = time.time()
    outputData = []
    
    with BytesIO() as buffer:
        start_time = time.time()

        while True:
            print('current time', time.time()-start_time)
            if time.time()-begin>timeout:
                break
            try:
                resp = s.recv(1024)
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
                    handle_line(line)       # Do something with your line
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
                    
    return outputData   

async def recv_linebyline_async(timeout=15):
    # TODO: asyncio connection object should be given a input parameter.
    begin = time.time()
    outputData = []
    s, writer = await asyncio.open_connection(
        HOST, PORT)
    
    with BytesIO() as buffer:
        start_time = time.time()

        while True:
            print('current time', time.time()-start_time)
            if time.time()-begin>timeout:
                break
            try:
                resp = await s.read(1024)
            except BlockingIOError:
                print("Sleeping")
                await asyncio.sleep(2)
            else:
                begin = time.time()
                buffer.write(resp)
                buffer.seek(0)
                start_index = 0  # Count the number of characters processed
                for line in buffer:
                    start_index += len(line)
                    handle_line(line)       # Do something with your line
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
                

def handle_line(line):
    line_str = line.decode('utf-8')
    if 'sta;add' in line_str:
        print('Station added')
        indexStr = line_str.find('sta;add')
        print('macaddr:', line_str[indexStr+10:indexStr+20])
    elif 'txs;' in line_str:
        print('Station present')
        indexStr = line_str.find('sta;add') + 4
        print('macaddr:', line_str[indexStr:indexStr+17])
    elif 'txs;macaddr' in line_str:
        print('Basic TX status')
        
    # elif sta; remove:
    #     ...
    # elif tx:
    #     ...
    # else:
    #     ...
    pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    # #data = recv_with_timeout(s)
    # end_marker = 'phy1;0;add\n'
    # data = recv_end(s, end_marker)
    # s.close()
    data = recv_linebyline(s)
    s.close()

if __name__ == "__main__":
    main()