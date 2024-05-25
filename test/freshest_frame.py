import cv2, queue, threading, time
# https://stackoverflow.com/questions/43665208/how-to-get-the-latest-frame-from-capture-device-camera-in-opencv
# bufferless VideoCapture
class VideoCapture:
  def __init__(self, name, arg = None):
    self.cap = cv2.VideoCapture(name, arg)
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

cap = VideoCapture('rtsp://10.3.141.1:8554/cam')
while True:
  #time.sleep(.5)   # simulate time between events
  frame = cap.read()
  frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
  frame = cv2.flip(frame, 1)
  cv2.imshow("frame", frame)
  if chr(cv2.waitKey(1)&255) == 'q':
    break