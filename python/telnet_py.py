import telnetlib

HOST = ""
PORT = 12345

def open(host, port):
    tn = telnetlib.Telnet(HOST, PORT)
    return tn


def close(tn):
    tn.close()


def main():
    tn = open(HOST, PORT)
    f = open('telnet_output.txt', "wb")
    f.write(bytes_outp)
    f.close()
    close(tn)

if __name__ == '__main__':
    main()
