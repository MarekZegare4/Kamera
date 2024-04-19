import RPi.GPIO as GPIO
import time
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import socket
import struct
import sys
import pickle

class wspolrzedne:
  def __init__(self, x, y):
    self.x = x
    self.y = y

factory = PiGPIOFactory()
servo = Servo(17, pin_factory=factory)
pozycja_sledzenia = 0
screen_width = 640

multicast_group = '224.0.0.0'
server_address = ('', 10000)
multicast_port = 6060
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((multicast_group, multicast_port))
group = socket.inet_aton(multicast_group)
mreq = struckt.pack('4sL', group, socket_INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

try:
  while True:
    data, address = sock.recvfrom(1024)
    message = pickle.loads(data)
    print('Odebrano X = ' + str(message.x))
    pozycja_do_norm = message.x
    if (pozycja_do_norm > screen_width/2):
      pozycja_sledzenia = (pozycja_do_norm - (screeen_width/2)) / (screen_width/2)
    if (pozycja_do_norm < screen_width/2):
      pozycja_sledzenia = (pozycja_do_norm / (screen_width/2)) * (-1)
    if (pozycja_do_norm == 0):
      pozycja_sledzenia = 0
    print("Pozycja sledzenia wynosi " + str(pozycja_sledzenia))
    while (pozycja_sledzenia < -0.05):
      servo.value = pozycja_sledzenia
      pozycja_sledzenia = pozycja_sledzenia + 0.01
      time.sleep(0.1)
    while (pozycja_sledzenia > 0.05):
      servo.value = pozycja_sledzenia
      pozycja_sledzenia = pozycja_sledzenia - 0.01
      time.sleep(0.1)
    servo.mid()
    time.sleep(2)

except KeyboardInterrupt:
  print("Koniec")
