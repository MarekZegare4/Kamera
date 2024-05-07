import socket
import time

host = socket.gethostname()
port = 6060        
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False

while not connected:
    try:
        s.connect((host, port))
        connected = True
    except socket.error as e:
        connected = False
        print("Błąd połączenia")
        time.sleep(1)

while True:
    data = s.recv(1024)
    print('Received', data.decode())
        