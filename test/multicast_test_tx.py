import socket
import struct
import time
import random
import pickle
import sys

class wspolrzedne:
    def __init__(self, x ,y):
        self.x = x
        self.y = y

multicast_group = ('224.0.0.0', 6060)

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 60)
while True:
    xy = wspolrzedne(random.randrange(0, 500), random.randrange(0, 500))
    try:
        message = pickle.dumps(xy)
        # Send data to the multicast group
        print('Wysłano dane')
        sock.sendto(message, multicast_group)

        # Look for responses from all recipients
    except Exception as e:
        print(e)
    time.sleep(1)