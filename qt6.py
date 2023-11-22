import sys
import os
import cv2
from PyQt6 import QtGui
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
from ultralytics import YOLO
import numpy as np

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'

# Adres streamu wideo
RTSP_URL = 'http://173.162.200.86:3123/mjpg/video.mjpg?resolution=1280x1024&compression=30&mirror=0&rotation=0&textsize=small&textposition=b'

# Wybór modelu 
model = YOLO('yolov8n.pt')

frame = []
switch = False

# Główne okno
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My App")
        self.setMinimumSize(QSize(400, 300))
        self.disply_width = int(800)
        self.display_height = int(600)

        # Wyświetlanie wideo
        self.orgvid_label = QLabel(self)
        self.modvid_label = QLabel(self)

        # Przycisk do włączania/wyłączania modelu
        model_on = QPushButton()
        model_on.setText("Model toggle")
        model_on.pressed.connect(self.Click)

        # Połoenie elementów w oknie
        layout = QGridLayout()
        widget = QWidget()
        widget.setLayout(layout)
        layout.addWidget(self.orgvid_label, 1, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.modvid_label, 1, 2, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(model_on, 2, 1, Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(widget)

        # Deklaracja wątków
        self.video_thread = VideoThread()
        self.model_thread = ModelThread()

        # Połączenie wyjściowych wideo do wyświeltania
        self.video_thread.oryg_video.connect(self.update_orgvid)
        self.model_thread.model_video.connect(self.update_modvid)

        self.video_thread.start()
        self.model_thread.start()

    # Metoda zarządzająca kliknięciem przycisku
    def Click(self):
        global switch
        switch = not switch
        if switch:
            self.model_thread.model_video.connect(self.update_modvid)
        else:
            self.video_thread.oryg_video.connect(self.update_modvid)
    
    # Metody akutalizujące wyświetlany obraz w oknie
    @pyqtSlot(np.ndarray)
    def update_orgvid(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.orgvid_label.setPixmap(qt_img)
        
    @pyqtSlot(np.ndarray)
    def update_modvid(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.modvid_label.setPixmap(qt_img)
    
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
    global screen_size
    def run(self):
        global frame 
        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        while True:
            ret, cv_img = cap.read()
            if ret:
                frame = cv_img
                self.oryg_video.emit(cv_img)

# Wątek opdowiedzialny za przepuszczanie klatek przez model
class ModelThread(QThread):
    model_video = pyqtSignal(np.ndarray)
    def run(self):
        global frame
        while True:
            if len(frame) > 0 and switch:
                results = model.track(frame, persist=True, show_labels=True)
                annotated_frame = results[0].plot()
                self.model_video.emit(annotated_frame)


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()