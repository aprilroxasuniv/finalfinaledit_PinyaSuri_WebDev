import numpy as np
import tensorflow as tf
from PIL import Image
import json
import os

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "upload_model.tflite")
LABEL_PATH = os.path.join(BASE_DIR, "labels.json")

# ================= LOAD MODEL =================
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# ================= LOAD LABELS =================
with open(LABEL_PATH, "r") as f:
    labels = json.load(f)

# ================= ANALYZE IMAGE =================
def analyze_upload_image(image_path):
    # Load image
    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224))

    # Normalize
    input_data = np.expand_dims(
        np.array(img, dtype=np.float32) / 255.0,
        axis=0
    )

    # Run inference
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]["index"])[0]

    # Get prediction
    class_id = int(np.argmax(output))
    confidence = float(output[class_id])

    return [{
        "affliction": labels[str(class_id)],
        "confidence": confidence
    }]