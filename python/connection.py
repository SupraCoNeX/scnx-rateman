import socket

HOST = ""
PORT = 12345

def open(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s

def close(s):
    s.close()

def main():
    s = open(HOST, PORT)
    data = s.recv(100000)
    s.close()
    print(repr(data))

if __name__ == "__main__":
    main()
