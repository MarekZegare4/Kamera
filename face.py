import cv2
import os

# Load the cascade
face_cascade = cv2.CascadeClassifier('/Users/jakub/Desktop/opencv/opencv/data/lbpcascades/lbpcascade_frontalface_improved.xml')

# To capture video from webcam. 
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
RTSP_URL = 'http://camera.buffalotrace.com/mjpg/video.mjpg'
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
# To use a video file as input 
# cap = cv2.VideoCapture('filename.mp4')

while True:
    # Read the frame
    ret, img = cap.read()
    if ret == False:
        print("error")
    else:
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Detect the faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        # Draw the rectangle around each face
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        # Display
        cv2.imshow('TEST KAMERY', img)
        # Stop if escape key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
# Release the VideoCapture object
cap.release()