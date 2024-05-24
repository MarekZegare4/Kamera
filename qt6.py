import sys
import os
import cv2
from PyQt6 import QtGui
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
import cv2.data
from ultralytics import YOLO
import numpy as np
import torch
import time
import socket
import queue
import threading
import struct

move_coeff = 0

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
#os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'webrtc_transport'

# Wybór modelu 
model = YOLO('yolov8n.pt')
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Wybranie GPU jezeli dostępne
#device: str = "mps" if torch.backends.mps.is_available() else "cpu"
device = "cpu"
model.to(device)

frame = []
switch = False
mutex = QMutex()

multicast_group = ('224.0.0.0', 6060)

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 60)

# Adres streamu wideo
#url = 'http://173.162.200.86:3123/mjpg/video.mjpg?resolution=1280x1024&compression=30&mirror=0&rotation=0&textsize=small&textposition=b'
#url = 'http://63.142.183.154:6103/mjpg/video.mjpg'
#url = 'http://77.110.203.114:82/mjpg/video.mjpg'
#url = 'rtsp://192.168.0.103:8554/cam'
#url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

url = 'rtsp://10.3.141.1:8554/cam'
#url = 'rtsp://10.3.141.1:8889/cam'


font = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 2
color = (255,0,255)
thickness = 3

# https://stackoverflow.com/questions/43665208/how-to-get-the-latest-frame-from-capture-device-camera-in-opencv
# bufferless VideoCapture
class VideoCapture:
  def __init__(self, name, arg = None):
    self.cap = cv2.VideoCapture(name, arg)
    self.width = self.cap.get(3)
    self.height = self.cap.get(4)
    self.q = queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

  # read frames as soon as they are available, keeping only most recent one
  def _reader(self):
    while True:
      ret, frame = self.cap.read()
      if not ret:
        break
      if not self.q.empty():
        try:
          self.q.get_nowait()   # discard previous (unprocessed) frame
        except queue.Empty:
          pass
      self.q.put(frame)

  def read(self):
    return self.q.get()

# Główne okno
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kamera")
        self.setMinimumSize(QSize(1000, 600))
        self.resize(self.sizeHint())
        
        self.central_widget = QWidget()
        self.layout = QVBoxLayout()
        #self.set_widget = SettingsWidget()
        self.vid_widget = VideoWidget()

        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(self.layout)

        self.layout.addWidget(self.vid_widget)
        #self.layout.addWidget(self.set_widget)
        
 
class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        #self.layout = QVBoxLayout()
        #self.setLayout(self.layout)
        label = QLabel(self)
        label.setText("Ustawienia")
        label.move(10, 80)

        self.url_box = QLineEdit(self)
        self.url_box.move(10, 130)
        self.url_box.resize(200, 25)

        url_button = QPushButton(self)
        url_button.move(210, 130)
        url_button.setText("Ok")
        url_button.clicked.connect(self.set_url)

        combo = QComboBox(self)
        combo.move(10, 100)
        combo.addItem('n')
        combo.addItem('s')
        combo.addItem('m')
        combo.addItem('l')
        combo.addItem('x')

        combo.currentIndexChanged.connect(self.set_model)
        #self.layout.addWidget(self.label)
        #self.layout.addWidget(combo)

    def set_model(self, index):
        global model
        if index == 0:
            model = YOLO('yolov8n.pt')
        if index == 1:
            model = YOLO('yolov8s.pt')
        if index == 2:
            model = YOLO('yolov8m.pt')
        if index == 3:
            model = YOLO('yolov8l.pt')
        if index == 4:
            model = YOLO('yolov8x.pt')

    def set_url(self):
        global url
        url = self.url_box.text()
        print(url)
        

class VideoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout2 = QHBoxLayout()
        self.setLayout(self.layout)
        self.label = QLabel('Video')
        self.orgvid_label = QLabel(self)
        self.orgvid_label.resize(640, 480)  # Początkowy rozmiar, może być dowolny

        model_on = QPushButton()
        model_on.setText("Model toggle")
        model_on.pressed.connect(self.Click)

        move_left = QPushButton()
        move_left.setText("<")


        self.layout.addWidget(self.label)
        self.layout.addWidget(self.orgvid_label, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(model_on)
        self.layout.addWidget(move_left)

        self.video_thread = VideoThread()
        self.model_thread = ModelThread()
        self.com_thread = CommThread()

        self.com_thread.start()
        self.video_thread.start()
        self.video_thread.oryg_video.connect(self.update_orgvid)

    def Click(self):
        global switch
        switch = not switch
        if switch:
            self.model_thread.start()
            self.video_thread.oryg_video.disconnect(self.update_orgvid)
            self.model_thread.model_video.connect(self.update_orgvid)
        else:
            self.model_thread.stop()
            self.model_thread.model_video.disconnect(self.update_orgvid)
            self.video_thread.oryg_video.connect(self.update_orgvid)
    

    @pyqtSlot(np.ndarray)
    def update_orgvid(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.orgvid_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        # Pobierz aktualne wymiary widgetu, na którym ma być wyświetlany obraz
        display_width = self.orgvid_label.width()
        display_height = self.orgvid_label.height()

        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(display_width, display_height, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)




# Wątek odpowiedzialny za pobranie klatek wideo ze źródła
class VideoThread(QThread):
    oryg_video = pyqtSignal(np.ndarray)
    active = True
    def run(self):
        self.active = True
        global frame
        global frame_width
        global frame_height
        #cap = VideoCapture(url, cv2.CAP_FFMPEG)
        cap = VideoCapture(2)
        frame_width = cap.width
        frame_height = cap.height
        while True:
            #mutex.lock()
            cv_img = cap.read()
            #cv_img = cv2.rotate(cv_img, cv2.ROTATE_90_CLOCKWISE)
            frame = cv_img
            self.oryg_video.emit(cv_img)
            time.sleep(0.03)
            #mutex.unlock()

    def stop(self):
        self.active = False
        self.wait()
   


#   Wątek opdowiedzialny za przepuszczanie klatek przez model
class ModelThread(QThread):
    model_video = pyqtSignal(np.ndarray)
    active = True
    def run(self):
        self.active = True
        global frame
        global connected
        global frame_width
        global frame_height
        global center
        global move_coeff
        p1 = (frame_width/4, frame_height)
        p2 = (frame_width/4, 0)
        v = 0
        poz = [0, frame_height/2]
        wariancja_pred = 1
        wariancja_pom = 10
        print(p1, p2)
        while self.active:
           # mutex.lock()
            if switch:
                left_border = int(frame_width - frame_width/5*3)
                right_border = int(frame_width - frame_width/5*2)
                if len(frame) > 0:
                    start_time = time.time()
                    results = model.track(frame, show_labels=True, classes = [0])
                    annotated_frame = results[0].plot()
                    #speed = results[0].speed["inference"]
                    result = results[0]
                    xywh_all = result.boxes.xywh.tolist()
                    if (len(xywh_all) > 0):
                        xywh = xywh_all[0]
                        # KALMAN
                        td = time.time() - start_time
                        poz_zmierz = list(xywh)
                        poz[0] = poz[0] + td*v
                        v_nowa = 1*v + wariancja_pred * td*td
                        L = v_nowa + wariancja_pom * td*td
                        wzm_kalmana = v_nowa/L
                        poz[0] += wzm_kalmana*(poz_zmierz[0] - poz[0])
                        v = (1 - wzm_kalmana)*v_nowa
                        #
                        center = (int(xywh[0]), int(xywh[1]))
                        cv2.circle(annotated_frame,center, 10, (0,0,255), -1)
                        cv2.circle(annotated_frame, (int(poz[0]), int(poz[1])), 10, (255,0,0), -1)
                        if (poz[0] > 0 and poz[0] < left_border):
                            move_coeff = -1 #  "right"
                        if (poz[0] >= left_border and poz[0] <= right_border):
                            move_coeff = 0 #  "stop"
                        elif (poz[0] > right_border):
                            move_coeff = 1  # "left"
                    cv2.rectangle(annotated_frame, (left_border, 0), (right_border, int(frame_height)), color, thickness)
                    cv2.putText(annotated_frame, str(round(1/(time.time() - start_time), 2))+" FPS", (50, 100), font, fontScale, color, thickness, cv2.LINE_AA)
                    cv2.putText(annotated_frame, str(move_coeff), (50, 150), font, fontScale, (0, 255, 0), thickness, cv2.LINE_AA)
                    self.model_video.emit(annotated_frame)
            #mutex.unlock()    

    def stop(self):
        self.active = False
        self.wait()

#   Wątek odpowiedzialny za komunikajcę z kamerą
class CommThread(QThread):
    def run(self):
        global connected
        while True:
            try:
                # Send data to the multicast group
                print('Wysłano dane')
                message = "działa"
                sock.sendto(message.encode(), multicast_group)
                # Look for responses from all recipients
            except:
                print("cos nie dziala")
            time.sleep(1)
       
    def stop(self):
        self.active = False
        self.wait()

app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()