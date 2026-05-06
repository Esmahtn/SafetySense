from ultralytics import YOLO
import sys

print("Loading model...")
try:
    model = YOLO("yolo11n.pt")
    print("Model loaded successfully")
    print(model.names)
except Exception as e:
    print(f"Error loading model: {e}")
