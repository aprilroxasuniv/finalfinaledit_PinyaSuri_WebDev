import numpy as np
from PIL import Image
import tensorflow as tf

interpreter = tf.lite.Interpreter(model_path="ai/upload_model.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

with open("ai/labels.json", "r") as f:
    labels = json.load(f)

def analyze_upload_image(image_path):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224))

    input_data = np.expand_dims(
        np.array(img, dtype=np.float32) / 255.0,
        axis=0
    )

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]["index"])[0]

    class_id = int(np.argmax(output))
    confidence = float(output[class_id])

    return [{
        "affliction": labels[str(class_id)],
        "confidence": round(confidence, 3)
    }]