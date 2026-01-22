from flask import Flask, render_template, request, jsonify
import json
import os
import random
from werkzeug.utils import secure_filename
from datetime import datetime
from ai.upload_ai import analyze_upload_image


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_FILE = os.path.join(BASE_DIR, "data",  "logs.json")

UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(LOGS_FILE):
    with open(LOGS_FILE, "w") as f:
        json.dump([], f)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r") as f:
            return json.load(f)
    return []

def save_logs(logs):
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)

# ================= BASIC PAGES =================

@app.route('/')
def splash():
    return render_template('splash.html')


@app.route('/homepage')
def homepage():
    return render_template('homepage.html')


@app.route('/upload-section')
def upload_section():
    return render_template('upload-section.html')


@app.route('/management-strategies')
def management_strategies():
    selected_affliction = request.args.get("affliction")

    return render_template(
        "management-strategies.html",
        selected_affliction=selected_affliction
    )


# ================= DATA LOGS =================

@app.route("/data-logs")
def data_logs():
    logs = load_logs()

    for log in logs:
        if log.get("type") == "upload" and "date" not in log:
            old_dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            log["date"] = old_dt.strftime("%B %d, %Y")
            log["time"] = old_dt.strftime("%H:%M:%S")
            log["timestamp"] = f"{log['date']} {log['time']}"

    save_logs(logs)
    return render_template("data-logs.html", logs=logs)

# ================= DATA LOG ID DETAIL =================
#@app.route("/data-log/<log_id>")
#def data_log_detail(log_id):
#    logs = load_logs()
#
#    log = next(
#        (l for l in logs if l.get("type") == "flight" and l.get("id") == log_id),
#        None
#    )
#
#    if not log:
#        return "Flight log not found", 404
#
#    return render_template("data-log-detail.html", log=log)

@app.route("/data-log/<log_id>")
def data_log_detail(log_id):
    logs = load_logs()

    log = next(
        (l for l in logs if l.get("type") == "flight" and l.get("id") == log_id),
        None
    )

    if not log:
        return "Flight log not found", 404

    return render_template("data-log-detail.html", log=log)

# ================= API (RASPBERRY PI) =================
# ---------------- ROUTES ---------------- #
@app.route("/api/save-upload-result", methods=["POST"])
def save_upload_result():
    image = request.files.get("image")

    if not image:
        return jsonify({"message": "No image provided"}), 400

    now = datetime.now()
    date = now.strftime("%B %d, %Y")
    time = now.strftime("%H:%M:%S")
    timestamp = f"{date} {time}"

    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    image_relative_path = f"uploads/{filename}"

    

    # ✅ RUN AI
    ai_results = analyze_upload_image(image_path)

    normalized_afflictions = [
    {
        "affliction": a["affliction"],
        "confidence": a["confidence"]
    }
    for a in ai_results
]

    primary = ai_results[0]
    primary_affliction = primary["affliction"]
    primary_confidence = primary["confidence"]

    recommendation = (
        "No disease detected"
        if primary_affliction.lower().startswith("healthy")
        else "Apply appropriate treatment"
    )

    log_entry = {
        "type": "upload",
        "date": date,
        "time": time,
        "image": image_relative_path,
        "affliction": primary_affliction,
        "afflictions": normalized_afflictions,   # MULTI-LABEL
        "confidence": primary_confidence,
        "recommendation": recommendation,
        "timestamp": timestamp
    }

    logs = load_logs()
    logs.append(log_entry)
    save_logs(logs)

    print("AI RESULT:", normalized_afflictions)

    return jsonify({
        "message": "Data log saved successfully",
        "affliction": primary_affliction,
        "confidence": primary_confidence,
        "afflictions": ai_results,
        "recommendation": recommendation
    }), 201



#@app.route("/api/upload-flight-log", methods=["POST"])
#def upload_flight_log():
#    try:
#        metadata = json.loads(request.form.get("metadata", "{}"))
#        images = request.files.getlist("images")
#
#        flight_id = metadata.get("flight_id")
#        date = metadata.get("date")
#        start_time = metadata.get("start_time")
#        end_time = metadata.get("end_time")
#
#        if not flight_id or not images:
#            return jsonify({"error": "Missing flight_id or images"}), 400
#
#        logs = load_logs()
#
#        waypoints = []
#        affliction_counter = {}
#        healthy_count = 0
#
#        preview_image = "images/placeholder.jpg"
#
#
#        for idx, img in enumerate(images):
#            filename = secure_filename(img.filename)    
#            img.save(os.path.join(UPLOAD_FOLDER, filename))
#
#            if idx == 0:
#                preview_image = f"uploads/{filename}"
#
#
#            # 🔁 Placeholder AI (replace later)
#            affliction = random.choice([
#                "Healthy Pineapple",
#                "Crown Rot Disease",
#                "Fruit Rot Disease",
#                "Mealybug Wilt Disease",
#                "Root Rot Disease",
#                "Multiple Crown Disorder",
#                "Fruit Fasciation Disorder"
#            ])
#            confidence = round(random.uniform(0.85, 0.99), 2)
#
#            recommendation = (
#                "No disease detected"
#                if affliction == "Healthy Pineapple"
#                else "Apply appropriate treatment"
#            )
#
#            if affliction == "Healthy Pineapple":
#                healthy_count += 1
#            else:
#                affliction_counter[affliction] = affliction_counter.get(affliction, 0) + 1
#
#            waypoints.append({
#                "waypoint_id": f"WP{idx+1}",
#                "image": f"uploads/{filename}",   # ✅ FIX
#                "affliction": affliction,
#                "confidence": confidence,
#                "recommendation": recommendation
#            })
#
#
#        diseased_count = len(images) - healthy_count
#        dominant_affliction = (
#            max(affliction_counter, key=affliction_counter.get)
#            if affliction_counter else "None"
#        )
#
#        overall_risk = (
#            "Low" if diseased_count == 0 else
#            "Moderate" if diseased_count < len(images) / 2 else
#            "High"
#        )
#
#        flight_status = (
#            "Healthy" if diseased_count == 0 else "Attention Needed"
#        )
#
#        avg_confidence = round(
#            sum(wp["confidence"] for wp in waypoints) / len(waypoints),
#            2
#        ) if waypoints else 0
#
#        total_pineapples = healthy_count + diseased_count
#    
#    except Exception as e:
#        print(f"An error occurred: {e}")
#        return jsonify({"error": str(e)}), 500


#flight_log = {
#    "id": "FLIGHT_03",
#    "type": "flight",
#    "date": "January 21, 2026",
#    "start_time": "start_time",
#    "end_time": "end_time",
#    "image": "preview_image",
#
#    # ================= SUMMARY (MANUAL) =================
#    "summary": {
#        "total_waypoints": 3,
#        "captured_waypoints": 3,
#        "mission_status": "Completed",
#
#        "pineapples_detected": 24,
#        "healthy_pineapples": 10,
#        "afflicted_pineapples": 14,
#
#        "most_common_affliction": "Fruit Rot Disease",
#        "avg_confidence": 92.4
#    },
#
#    # ================= WAYPOINTS (MANUAL) =================
#    "waypoints": [
#        {
#            "waypoint_id": "WP1",
#            "image": "uploads/wp1.jpg",
#
#            "num_pineapples": 8,
#            "healthy": 3,
#            "afflicted": 5,
#
#            "afflictions": {
#                "Fruit Rot Disease": 2,
#                "Crown Rot Disease": 3
#            },
#
#            "avg_confidence": 91.2
#        },
#
#        {
#            "waypoint_id": "WP2",
#            "image": "uploads/wp2.jpg",
#
#            "num_pineapples": 9,
#            "healthy": 4,
#            "afflicted": 5,
#
#            "afflictions": {
#                "Fruit Rot Disease": 4,
#                "Mealybug Wilt Disease": 1
#            },
#
#            "avg_confidence": 94.8
#        },
#
#        {
#            "waypoint_id": "WP3",
#            "image": "uploads/wp3.jpg",
#
#            "num_pineapples": 7,
#            "healthy": 3,
#            "afflicted": 4,
#
#            "afflictions": {
#                "Fruit Rot Disease": 2,
#                "Root Rot Disease": 2
#            },
#
#            "avg_confidence": 90.5
#        }
#    ]
#}
#
#
#flight_log = {z
#            "id": flight_id,
#            "type": "flight",
#            "date": date,
#            "start_time": start_time,
#            "end_time": end_time,
#            "image": preview_image,
#            "summary": {
#                "total_waypoints": len(images),
#                "captured_waypoints": len(waypoints),
#                "mission_status": "Completed",
#                "pineapples_detected": total_pineapples,
#                "healthy_pineapples": healthy_count,
#                "afflicted_pineapples": diseased_count,
#                "most_common_affliction": dominant_affliction,
#                "avg_confidence": avg_confidence
#            },
#            "waypoints": waypoints
#        }
#
#logs.append(flight_log)
#save_logs(logs)
#
#return jsonify({
#            "status": "success",
#            "message": "Flight log uploaded successfully",
#            "flight_id": flight_id
#        })
#except Exception as e:
#return jsonify({"error": str(e)}), 500


@app.route("/api/analyze-upload", methods=["POST"])
def analyze_upload():
    image = request.files.get("image")
    if not image:
        return jsonify({"message": "No image provided"}), 400

    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    results = analyze_upload_image(image_path)
    primary = results[0]

    return jsonify({
        "affliction": primary["affliction"],
        "confidence": primary["confidence"],
        "afflictions": results,
        "recommendation": (
            "No disease detected"
            if primary["affliction"].lower().startswith("healthy")
            else "Apply appropriate treatment"
        )
    })

@app.route("/debug-logs")
def debug_logs():
    return jsonify(load_logs())

# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

