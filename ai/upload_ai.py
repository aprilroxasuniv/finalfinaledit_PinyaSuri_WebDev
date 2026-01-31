import numpy as np
import tensorflow as tf
from PIL import Image
import json
import os
import YOLO
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
    image = cv2.imread(image_path)
    if image is None:
        return [{
            "affliction": "Healthy Pineapple",
            "confidence": 0.8
        }]

    results = model.predict(
        source=image_path,
        conf=0.3,
        save=False
    )

    detections = []

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        # --- TFLITE CLASSIFICATION ---
        crop_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        crop_img = crop_img.resize((224, 224))
        input_data = np.expand_dims(np.array(crop_img, dtype=np.float32) / 255.0, axis=0)

        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]["index"])[0]

        class_id = int(np.argmax(output))
        confidence = float(output[class_id])

        detections.append({
            "affliction": labels[str(class_id)],
            "confidence": round(confidence, 3)
        })

    # Fallback
    if not detections:
        detections.append({
            "affliction": "Healthy Pineapple",
            "confidence": 0.85
        })

    return detections


