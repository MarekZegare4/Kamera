import socket

host = socket.gethostname()
port = 6060                   # The same port as used by the server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
while True:
    data = s.recv(1024)
    print('Received', data.decode())