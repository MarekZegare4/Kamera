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
import pyvirtualcam
import psutil
import openvino as ov

addrs = psutil.net_if_addrs()
for key in addrs:
    for addr in addrs[key]:
        if addr.address.startswith('10.3.141'):
            wifi_address = addr.address
    

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
# Wybór modelu 
model = YOLO('model/yolov8n.pt')
# Export the model
#model.export(format="openvino")  # creates 'yolov8n_openvino_model/'
# Load the exported OpenVINO model
ov_model = YOLO("model/yolov8n_openvino_model", task="detect")


# Wybranie GPU jezeli dostępne
#device: str = "mps" if torch.backends.mps.is_available() else "cpu"
device = "cpu"
model.to(device)

move_coeff = 0
frame = []
switch = False
debug = False
vcam = False
mutex = QMutex()
conf = 0.6

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
class VideoCapture(cv2.VideoCapture):
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
        self.setFixedSize(1000, 662)
        
        self.timer_left = QTimer()
        self.timer_right = QTimer()

        self.orgvid_label = QLabel(self)
        self.orgvid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orgvid_label.setGeometry(0, 0, 1000, 562)

        model = QPushButton(self)
        model.setText("Wykrywanie")
        model.clicked.connect(self.Click)
        model.setGeometry(0, 562, 1000, 25)

        left = QPushButton(self)
        left.setText("<")
        left.setGeometry(0, 587, 250, 75)
        left.pressed.connect(self.on_press_left)
        left.released.connect(self.on_release_left)
        self.timer_left.timeout.connect(self.send_left)

        center = QPushButton(self)
        center.setText("O")
        center.clicked.connect(self.send_center)
        center.setGeometry(250, 587, 250, 75)

        right = QPushButton(self)
        right.setText(">")
        right.setGeometry(500, 587, 250, 75)
        right.pressed.connect(self.on_press_right)
        right.released.connect(self.on_release_right)
        self.timer_right.timeout.connect(self.send_right)

        settings = QPushButton(self)
        settings.setText("Ustawienia")
        settings.clicked.connect(self.show_settings)
        settings.setGeometry(850, 587, 150, 75)

        self.video_thread = VideoThread()
        self.model_thread = ModelThread()
        self.com_thread = CommThread()
        self.sett_widget = SettingsWidget()
        

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
    
    def on_release_left(self):
        self.timer_left.stop()
    
    def on_release_right(self):
        self.timer_right.stop()

    def on_press_left(self):
        self.timer_left.start(int(1000/30))
    
    def on_press_right(self):
        self.timer_right.start(int(1000/30))

    def send_left(self):
        global move_coeff
        move_coeff = -1
    
    # Ustawienie kamery na środku
    def send_center(self):
        global move_coeff
        move_coeff = 100
    
    def send_right(self):
        global move_coeff
        move_coeff = 1
    
    def show_settings(self):
        self.sett_widget.show()

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
    
    def closeEvent(self, event):
        QApplication.closeAllWindows()
        event.accept()
 
class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ustawienia")
        self.setFixedSize(400, 400)

        label1 = QLabel(self)
        label1.setText("Wybór modelu")
        label1.setGeometry(0, 0, 400, 50)
        combo = QComboBox(self)
        combo.setGeometry(0, 40, 400, 50)
        combo.addItem('n')
        combo.addItem('s')
        combo.addItem('m')
        combo.addItem('l')
        combo.addItem('x')

        self.checkbox = QPushButton(self)
        self.checkbox.setText("Debug")
        self.checkbox.setGeometry(0, 150, 400, 50)
        self.checkbox.clicked.connect(self.set_debug)

        self.virtual_cam = QPushButton(self)
        self.virtual_cam.setText("Kamera wirtualna")
        self.virtual_cam.setGeometry(0, 220, 400, 50)
        self.virtual_cam.clicked.connect(self.set_vcam)
        
        
        self.label2 = QLabel(self)
        self.label2.setText("Próg wykrywania: " + str(conf))
        self.label2.setGeometry(0, 270, 400, 20)
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setGeometry(0, 310, 400, 20)
        self.slider.setRange(60, 100)
        self.slider.valueChanged.connect(self.updateLabel)

        combo.currentIndexChanged.connect(self.set_model)

        self.vcam_thread = VirtualCamThread()

        if debug == False:
            self.checkbox.setStyleSheet("QPushButton { background-color: #FF7F7F }")
        else:
            self.checkbox.setStyleSheet("QPushButton { background-color: #90EE90 }")

        if vcam == False:
            self.virtual_cam.setStyleSheet("QPushButton { background-color: #FF7F7F }")
        else:
            self.virtual_cam.setStyleSheet("QPushButton { background-color: #90EE90 }")

    def updateLabel(self, value):
        global conf
        conf = value/100
        self.label2.setText("Próg wykrywania: " + str(conf))

    def set_vcam(self):
        global vcam
        if vcam == False:
            self.vcam_thread.start()
            self.virtual_cam.setStyleSheet("QPushButton { background-color: #90EE90 }")
            vcam = True
        else:
            self.vcam_thread.stop()
            self.virtual_cam.setStyleSheet("QPushButton { background-color: #FF7F7F }")
            vcam = False

    def set_debug(self):
        global debug
        if debug == False:
            debug = True
            self.checkbox.setStyleSheet("QPushButton { background-color: #90EE90 }")
        else:
            debug = False
            self.checkbox.setStyleSheet("QPushButton { background-color: #FF7F7F }")

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
        print("Kamera połączona")
        frame_width = cap.width
        frame_height = cap.height
        while True:
            try:
                cv_img = cap.read()
                frame = cv_img
                self.oryg_video.emit(cv_img)
            except Exception as e:
                print(e)

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
        global frame_width
        global frame_height
        global center
        global move_coeff
        global conf
        v = 0
        poz = [frame_width/2, frame_height/2]
        wariancja_pred = 1
        wariancja_pom = 10
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
                    results = ov_model.track(frame, show_labels=True, classes = [0], conf=conf)
                    annotated_frame = frame
                    cv2.circle(annotated_frame, (int(frame_width - 100), 100), 20, (0,255,0), -1)
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

                        if debug:
                            center = (int(xywh[0]), int(xywh[1]))
                            annotated_frame = results[0].plot()
                            cv2.circle(annotated_frame, center, 10, (0,0,255), -1)
                            cv2.circle(annotated_frame, (int(poz[0]), int(poz[1])), 10, (255,0,0), -1)
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
        global move_coeff
        sock.bind((wifi_address, 6060))
        while True:
            try:
                # Send data to the multicast group
                message = str(move_coeff)
                #print(message)
                sock.sendto(message.encode(), multicast_group)
                move_coeff = 0
                # Look for responses from all recipients
            except Exception as e:
                print(e)
            time.sleep(0.03)

class VirtualCamThread(QThread):
    def run(self):
        self.active = True
        global frame
        fmt = pyvirtualcam.PixelFormat.BGR
        with pyvirtualcam.Camera(width=1920, height=1080, fps=30, fmt=fmt) as cam:
            while self.active:
                try:
                    cam.send(frame)
                    cam.sleep_until_next_frame()
                except Exception as e:
                    print(e)

    def stop(self):
        self.active = False
        self.wait()
        
app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()