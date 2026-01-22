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

    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()

    output = interpreter.get_tensor(output_details[0]['index'])
    output = np.squeeze(output)

    print("RAW OUTPUT SHAPE:", output.shape)

    # ✅ Your model outputs [num_classes, num_detections]
    # We reduce detections → single confidence per class
    if output.ndim == 2:
        class_scores = np.max(output, axis=1)

    elif output.ndim == 1:
        class_scores = output

    else:
        raise ValueError(f"Unexpected output shape: {output.shape}")

    results = []

    for i, score in enumerate(class_scores):
        score = float(score)

        # safety check so labels never crash again
        if str(i) not in labels:
            continue

        if score >= 0.30:
            results.append({
                "affliction": labels[str(i)],
                "confidence": round(score, 3)
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)

    if not results:
        results.append({
            "affliction": "Healthy Pineapple",
            "confidence": 0.99
        })

    return results


