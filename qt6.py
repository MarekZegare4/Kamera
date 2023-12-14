import sys
import os
import cv2
from PyQt6 import QtGui
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
from ultralytics import YOLO
import numpy as np
import torch
import time

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'

# Wybór modelu 
model = YOLO('yolov8n.pt')

# Wybranie GPU jezeli dostępne
device: str = "mps" if torch.backends.mps.is_available() else "cpu"
model.to(device)

frame = []
switch = False
mutex = QMutex()

# Adres streamu wideo
#url = 'http://173.162.200.86:3123/mjpg/video.mjpg?resolution=1280x1024&compression=30&mirror=0&rotation=0&textsize=small&textposition=b'
url = 'http://63.142.183.154:6103/mjpg/video.mjpg'
#url = 'http://77.110.203.114:82/mjpg/video.mjpg'

font = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 2
color = (255,0,255)
thickness = 3

# Główne okno
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kamera")
        self.setMinimumSize(QSize(1000, 600))
        self.resize(self.sizeHint())
        
        self.central_widget = QWidget()
        self.layout = QHBoxLayout()
        self.set_widget = SettingsWidget()
        self.vid_widget = VideoWidget()

        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(self.layout)

        self.layout.addWidget(self.vid_widget)
        self.layout.addWidget(self.set_widget)
        
 
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
        self.setLayout(self.layout)
        self.label = QLabel('Video')
        self.orgvid_label = QLabel(self)
        self.orgvid_label.resize(self.orgvid_label.sizeHint()/2)

        self.disply_width = int(1920/2)
        self.display_height = int(1080/2)


        model_on = QPushButton()
        model_on.setText("Model toggle")
        model_on.pressed.connect(self.Click)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.orgvid_label, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(model_on)

        self.video_thread = VideoThread()
        self.model_thread = ModelThread()
    
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
        #self.orgvid_label.setScaledContents(True)
    
    # Zamiana wyjścia z opencv na format, który rozumie Qt
    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)



# Wątek odpowiedzialny za pobranie klatek wideo ze źródła
class VideoThread(QThread):
    oryg_video = pyqtSignal(np.ndarray)
    global url
    active = True
    def run(self):
        self.active = True
        global frame
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        url_buf1 = url
        while True:
            mutex.lock()
            if url_buf1 != url:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                url_buf1 = url
            ret, cv_img = cap.read()
            if ret:
                frame = cv_img
                self.oryg_video.emit(cv_img)
            mutex.unlock()

    def stop(self):
        self.active = False
        self.wait()
   


# Wątek opdowiedzialny za przepuszczanie klatek przez model
class ModelThread(QThread):
    model_video = pyqtSignal(np.ndarray)
    active = True
    def run(self):
        self.active = True
        global frame
        while self.active:
            mutex.lock()
            if switch:
                if len(frame) > 0:
                    start_time = time.time()
                    results = model.track(frame, show_labels=True)
                    annotated_frame = results[0].plot()
                    #speed = results[0].speed["inference"]
                    for result in results:
                        xywh = result.boxes.xywh.tolist()
                        if xywh != 0:
                            for i in xywh:
                                center = (int(i[0]), int(i[1]))
                                cv2.circle(annotated_frame,center, 10, (0,0,255), -1)
                   # lag = time.time() - start_time
                   # if lag < 0.033: # ograniczenie FPS do 30
                   #     time.sleep(0.033 - lag)
                    cv2.putText(annotated_frame, str(round(1/(time.time() - start_time), 2))+" FPS", (50, 100), font, fontScale, color, thickness, cv2.LINE_AA)
                    self.model_video.emit(annotated_frame)
            mutex.unlock()    

    def stop(self):
        self.active = False
        self.wait()

app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()