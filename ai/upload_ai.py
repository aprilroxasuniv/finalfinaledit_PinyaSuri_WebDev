import numpy as np
import tensorflow as tf
from PIL import Image
import json
import os
from ultralytics import YOLO
import cv2

model = YOLO("runs/detect/train5 (v8n)/weights/best.pt")

LABEL_PATH = "ai/labels.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "upload_model.tflite")

# Load model
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Load labels
with open(LABEL_PATH) as f:
    labels = json.load(f)

def analyze_upload_image(image_path):
    results = model.predict(
        source=image_path,
        conf=0.3,
        save=False
    )

    detections = []

    for box in results[0].boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        detections.append({
            "affliction": CLASS_NAMES.get(class_id, "Unknown"),
            "confidence": confidence
        })

    # ❗ fallback if no detections
    if not detections:
        detections.append({
            "affliction": "Healthy Pineapple",
            "confidence": 0.85
        })

    return detections


