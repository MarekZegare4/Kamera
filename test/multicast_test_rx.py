import socket
import struct
import sys
import pickle

class wspolrzedne:
    def __init__(self, x ,y):
        self.x = x
        self.y = y

multicast_group = '224.0.0.0'
server_address = ('', 10000)
multicast_port = 6060
# Create the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind to the server address
sock.bind((multicast_group, multicast_port))
# Tell the operating system to add the socket to the multicast group
# on all interfaces.
group = socket.inet_aton(multicast_group)
mreq = struct.pack('4sL', group, socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
while True:
    data, address = sock.recvfrom(1024)
    message = data.decode('utf-8')
    print(message)


