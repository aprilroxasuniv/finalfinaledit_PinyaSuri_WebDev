from ultralytics import YOLO
import cv2
import os
import numpy as np

# Load YOLO model ONCE
model = YOLO("ai/best.pt", task="detect") # your trained model

# ✅ CLASS ID → NAME
CLASS_NAMES = {
    0: "Crown Rot Disease",
    1: "Fruit Fascination Disorder",
    2: "Fruit Rot Disease",
    3: "Healthy",
    4: "Mealybug Wilt Disease",
    5: "Multiple Crown Disorder",
    6: "Root Rot Disease"
}

def analyze_upload_image(image_path):
    results = model(image_path, conf=0.3)

    detections = []  # ✅ IMPORTANT

    for r in results:
        if r.boxes is None:
            continue

        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])

            label = CLASS_NAMES.get(cls_id, f"class{cls_id}")

            detections.append({
                "affliction": label,
                "confidence": round(conf * 100, 2)
            })

    # ✅ If nothing detected
    if not detections:
        return {
            "affliction": "Healthy Pineapple",
            "confidence": 95,
            "afflictions": []
        }

    # ✅ Highest confidence = main affliction
    main = max(detections, key=lambda x: x["confidence"])

    return {
        "affliction": main["affliction"],
        "confidence": main["confidence"],
        "afflictions": detections
    }