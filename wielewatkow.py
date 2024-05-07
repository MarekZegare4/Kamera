import cv2 
import time 
from threading import Thread
from ultralytics import YOLO
import os

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
model = YOLO('yolov8n.pt')
video_path = 'rtsp://192.168.0.107:8554/cam'

scale_percent = 100
#width = 300
#height = 200

# defining a helper class for implementing multi-threaded processing 
class WebcamStream :
    def __init__(self, stream_id):
        self.stream_id = stream_id   # default is 0 for primary camera 
        
        # opening video capture stream 
        self.vcap = cv2.VideoCapture(self.stream_id, cv2.CAP_FFMPEG)
        if self.vcap.isOpened() is False :
            print("[Exiting]: Error accessing webcam stream.")
            exit(0)
        fps_input_stream = int(self.vcap.get(5))
        print("FPS of webcam hardware/input stream: {}".format(fps_input_stream))
            
        # reading a single frame from vcap stream for initializing 
        self.grabbed , self.frame = self.vcap.read()
        if self.grabbed is False :
            print('[Exiting] No more frames to read')
            exit(0)
# self.stopped is set to False when frames are being read from self.vcap stream 
        self.stopped = True
# reference to the thread for reading next available frame from input stream 
        self.t = Thread(target=self.update, args=())
        self.t.daemon = True # daemon threads keep running in the background while the program is executing 
        
    # method for starting the thread for grabbing next available frame in input stream 
    def start(self):
        self.stopped = False
        self.t.start()
# method for reading next frame 
    def update(self):
        while True :
            if self.stopped is True :
                break
            self.grabbed , self.frame = self.vcap.read()
            if self.grabbed is False :
                print('[Exiting] No more frames to read')
                self.stopped = True
                break 
        self.vcap.release()
# method for returning latest read frame 
    def read(self):
        return self.frame
# method called to stop reading frames 
    def stop(self):
        self.stopped = True
# initializing and starting multi-threaded webcam capture input stream 
webcam_stream = WebcamStream(stream_id= video_path)
webcam_stream.start()
# processing frames in input stream
num_frames_processed = 0 
start = time.time()
while True :
    if webcam_stream.stopped is True :
        break
    else :
        frame = webcam_stream.read()
# adding a delay for simulating time taken for processing a frame
    width = int(frame.shape[1] * scale_percent / 100)
    height = int(frame.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
    results = model.track(resized, persist=True, show_labels=False)
    # Visualize the results on the frame
    annotated_frame = results[0].plot()
    num_frames_processed += 1
    cv2.imshow('RS' , annotated_frame)
    #cv2.imshow('OG' , frame)
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
end = time.time()
webcam_stream.stop() # stop the webcam stream
# printing time elapsed and fps 
elapsed = end-start
fps = num_frames_processed/elapsed 
print("FPS: {} , Elapsed Time: {} , Frames Processed: {}".format(fps, elapsed, num_frames_processed))
# closing all windows 
cv2.destroyAllWindows()