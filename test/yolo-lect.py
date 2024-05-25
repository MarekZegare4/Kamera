from ultralytics import YOLO

# Load a model
model = YOLO('yolov8n.pt')  # load an official detection model
#model = YOLO('yolov8n-seg.pt')  # load an official segmentation model
#model = YOLO('path/to/best.pt')  # load a custom model

# Track with the model
results = model.track(source="rtsp://rtsp.stream/movie", show=True)
#results = model.track(source="rtsp://192.168.0.107:8554/cam", show=True, tracker="bytetrack.yaml")
