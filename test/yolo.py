import cv2
from ultralytics import YOLO
import os
from threading import Thread

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'

model = YOLO('yolov8n.pt')

#video_path = 'http://212.170.100.189/mjpg/video.mjpg?timestamp=1580392032581'
video_path = 'rtsp://192.168.0.107:8554/cam'

cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)

scale_percent = 15 
width = 300
height = 200

while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()
    dim = (width, height)
    width = int(frame.shape[1] * scale_percent / 100)
    height = int(frame.shape[0] * scale_percent / 100)
    resized = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)

    if success:
        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        results = model.track(resized, persist=True, classes=[0,1], hide_labels=False)

        # Visualize the results on the frame
        annotated_frame = results[0].plot()

        # Display the annotated frame
        cv2.imshow("YOLOv8 Tracking", annotated_frame)
        #cv2.imshow("Untracked", resized)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        # Break the loop if the end of the video is reached
        break

# Release the video capture object and close the display window
cap.release()
cv2.destroyAllWindows()




