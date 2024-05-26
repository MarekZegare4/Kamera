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
import time
import socket
import queue
import threading
import struct

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
# Wybór modelu 
model = YOLO('model/yolov8s.pt')

# Wybranie GPU jezeli dostępne
#device: str = "mps" if torch.backends.mps.is_available() else "cpu"
device = "cpu"
model.to(device)

move_coeff = 0
frame = []
switch = False
mutex = QMutex()

multicast_group = ('224.0.0.0', 6060)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

url = 'rtsp://10.3.141.1:8554/cam'

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
        self.setFixedSize(800, 900)
        
        self.orgvid_label = QLabel(self)
        self.orgvid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orgvid_label.setGeometry(0, 0, 800, 800)

        model = QPushButton(self)
        model.setText("Model toggle")
        model.clicked.connect(self.Click)
        model.setGeometry(0, 800, 800, 25)

        left = QPushButton(self)
        left.setText("<")
        left.clicked.connect(self.send_left)
        left.setGeometry(0, 825, 200, 75)

        center = QPushButton(self)
        center.setText("O")
        center.clicked.connect(self.send_center)
        center.setGeometry(200, 825, 200, 75)

        right = QPushButton(self)
        right.setText(">")
        right.clicked.connect(self.send_right)
        right.setGeometry(400, 825, 200, 75)

        settings = QPushButton(self)
        settings.setText("Ustawienia")
        settings.clicked.connect(self.show_settings)
        settings.setGeometry(650, 825, 150, 75)

        self.video_thread = VideoThread()
        self.model_thread = ModelThread()
        self.com_thread = CommThread()

        self.com_thread.start()
        self.video_thread.start()
        self.video_thread.oryg_video.connect(self.update_orgvid)
        print(self.orgvid_label.size())

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
    
    def send_left(self):
        global move_coeff
        move_coeff = -1
    
    # Ustawienie kamery na środku
    def send_center(self):
        global move_coeff
        move_coeff = 10
    
    def send_right(self):
        global move_coeff
        move_coeff = 1
    
    def show_settings(self):
        self.set_widget = SettingsWidget()
        self.set_widget.show()

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

        # self.central_widget = QWidget()

        #self.set_widget = SettingsWidget()
        #self.vid_widget = VideoWidget()
        #self.buttons_widget = ButtonsWidget()

        # self.setCentralWidget(self.central_widget)
        # self.central_widget.setLayout(self.layout)

        # self.layout.addWidget(self.vid_widget)
        # self.layout.addWidget(self.buttons_widget)
        #self.layout.addWidget(self.set_widget)
        
 
class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ustawienia")
        self.setFixedSize(400, 400)

        label1 = QLabel(self)
        label1.setText("Wybór modelu")
        label1.setGeometry(0, 0, 400, 50)
        combo = QComboBox(self)
        combo.setGeometry(0, 70, 400, 50)
        combo.addItem('n')
        combo.addItem('s')
        combo.addItem('m')
        combo.addItem('l')
        combo.addItem('x')

        combo.currentIndexChanged.connect(self.set_model)

    def set_model(self, index):
        global model
        if index == 0:
            model = YOLO('model/yolov8n.pt')
        if index == 1:
            model = YOLO('model/yolov8s.pt')
        if index == 2:
            model = YOLO('model/yolov8m.pt')
        if index == 3:
            model = YOLO('model/yolov8l.pt')
        if index == 4:
            model = YOLO('model/yolov8x.pt')

    def set_url(self):
        global url
        url = self.url_box.text()
        print(url)
        


# Wątek odpowiedzialny za pobranie klatek wideo ze źródła
class VideoThread(QThread):
    oryg_video = pyqtSignal(np.ndarray)
    active = True
    def run(self):
        self.active = True
        global frame
        global frame_width
        global frame_height
        cap = VideoCapture(url, cv2.CAP_FFMPEG)
        frame_width = cap.width
        frame_height = cap.height
        while True:
            try:
                cv_img = cap.read()
                frame = cv_img
                self.oryg_video.emit(cv_img)
                time.sleep(0.03)
            except Exception as e:
                print(e)
                break

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
                left2_border = int(frame_width/5)
                left3_border = int(0)
                right_border = int(frame_width - frame_width/5*2)
                right2_border = int(frame_width - frame_width/5)
                right3_border = int(frame_width)
                if len(frame) > 0:
                    start_time = time.time()
                    results = model.track(frame, show_labels=True, classes = [0], conf=0.75)
                    annotated_frame = results[0].plot()
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

                        # Strefy prędkości obracania
                        if (poz[0] >= 0 and poz[0] < left2_border):
                            move_coeff = -2 #  "right"
                        if (poz[0] >= left2_border and poz[0] < left_border):
                            move_coeff = -1 #  "right"
                        if (poz[0] >= left_border and poz[0] <= right_border):
                            move_coeff = 0 #  "stop"
                        if (poz[0] >= right_border and poz[0] < right2_border):
                            move_coeff = 1
                        elif (poz[0] >= right2_border):
                            move_coeff = 2  # "left"
                        
                    cv2.rectangle(annotated_frame, (left_border, 0), (right_border, int(frame_height)), color, thickness)
                    cv2.rectangle(annotated_frame, (right_border, 0), (right2_border, int(frame_height)), (100, 136, 120), thickness)
                    cv2.rectangle(annotated_frame, (right2_border, 0), (right3_border, int(frame_height)), (255, 255, 120), thickness)
                    cv2.rectangle(annotated_frame, (left2_border, 0), (left_border, int(frame_height)), (100, 136, 120), thickness)
                    cv2.rectangle(annotated_frame, (left3_border, 0), (left2_border, int(frame_height)), (255, 255, 120), thickness)

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
        global move_coeff
        while True:
            try:
                # Send data to the multicast group
                message = str(move_coeff)
                print(message)
                sock.sendto(message.encode(), multicast_group)
                move_coeff = 100
                # Look for responses from all recipients
            except Exception as e:
                print(e)
            time.sleep(0.2)
       
    def stop(self):
        self.active = False
        self.wait()

app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()