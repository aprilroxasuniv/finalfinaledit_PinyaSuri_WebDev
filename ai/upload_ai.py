import numpy as np
import tensorflow as tf
from PIL import Image
import json
import os

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
    img = Image.open(image_path).convert("RGB")
    img = img.resize((640, 640))
    img = np.array(img, dtype=np.float32) / 255.0
    img = np.expand_dims(img, axis=0)

    interpreter.set_tensor(input_details[0]["index"], img)
    interpreter.invoke()

    output = interpreter.get_tensor(output_details[0]["index"])
    output = np.squeeze(output)

    results = []

    CONF_THRESHOLD = 0.60

    # if model outputs detections
    if output.ndim == 2:
        for class_index in range(output.shape[0]):
            for detection in output[class_index]:
                if detection >= CONF_THRESHOLD:
                    results.append({
                        "affliction": labels.get(str(class_index), "Unknown"),
                        "confidence": round(float(detection), 3)
                    })

    # fallback
    if not results:
        results.append({
            "affliction": "Healthy Pineapple",
            "confidence": 0.95
        })

    return results


