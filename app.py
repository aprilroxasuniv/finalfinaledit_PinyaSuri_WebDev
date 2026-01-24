from flask import Flask, render_template, request, jsonify
import json
import os
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

    filename = f"{int(now.timestamp())}_{secure_filename(image.filename)}"
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    image_relative_path = f"uploads/{filename}"

    ai_results = analyze_upload_image(image_path)
    if not ai_results:
        return jsonify({"error": "AI returned no results"}), 500

    normalized_afflictions = [
        {"affliction": a["affliction"], "confidence": a["confidence"]}
        for a in ai_results
    ]

    primary = ai_results[0]

    recommendation = (
        "No disease detected"
        if primary["affliction"].lower().startswith("healthy")
        else "Apply appropriate treatment"
    )

    log_entry = {
        "id": f"upload-{int(now.timestamp())}",
        "type": "upload",
        "date": date,
        "time": time,
        "image": image_relative_path,
        "affliction": primary["affliction"],
        "afflictions": normalized_afflictions,
        "confidence": primary["confidence"],
        "recommendation": recommendation,
        "timestamp": timestamp,
    }

    logs = load_logs()
    logs.append(log_entry)
    save_logs(logs)

    return jsonify({
        "message": "Data log saved successfully",
        "affliction": primary["affliction"],
        "confidence": primary["confidence"],
        "afflictions": ai_results,
        "recommendation": recommendation
    }), 201


@app.route("/api/upload-flight-log", methods=["POST"])
def upload_flight_log():

    try:
        flight_log = request.get_json(force=True)

        if not flight_log:
                return jsonify({"error": "No JSON received"}), 400

        # safety checks
        required = ["id", "type", "summary", "waypoints"]
        for key in required:
            if key not in flight_log:
                return jsonify({"error": f"Missing {key}"}), 400

        logs = load_logs()
        if any(l.get("id") == flight_log["id"] for l in logs):
            return jsonify({"error": "Flight ID already exists"}), 409
            
        summary = flight_log["summary"]

        flight_log["summary"] = {
                "total_waypoints": summary.get("total_waypoints", 0),
                "completed_waypoints": summary.get("completed_waypoints", summary.get("captured_waypoints", 0)),
                "mission_status": summary.get("mission_status", "Unknown"),

                "pineapple_detected": summary.get("pineapple_detected", summary.get("pineapples_detected", 0)),
                "healthy": summary.get("healthy", summary.get("healthy_pineapples", 0)),
                "black_rot": summary.get("black_rot", summary.get("afflicted_pineapples", 0)),

                "common_affliction": summary.get("common_affliction", summary.get("most_common_affliction", "—")),
                "average_confidence": round(summary.get("average_confidence", summary.get("avg_confidence", 0)), 1)
            }

        for wp in flight_log["waypoints"]:

                # 🔧 MAP RASPI FIELD → WEBSITE FIELD
                wp["total"] = wp.get("total", wp.get("num_pineapples", 0))

                # Normalize images
                if "images" not in wp:
                    if "image" in wp:
                        wp["images"] = [wp["image"]]
                        del wp["image"]
                    else:
                        wp["images"] = []

                # 🔒 Limit to 5 images
                wp["images"] = wp["images"][:5]

                # Ensure afflictions dict exists
                wp.setdefault("afflictions", {})

                # Ensure numeric fields exist
                wp.setdefault("total", 0)
                wp.setdefault("healthy", 0)
                wp.setdefault("afflicted", 0)

        logs.append(flight_log)
        save_logs(logs)

        return jsonify({
                "status": "success",
                "message": "Flight log saved",
                "flight_id": flight_log["id"]
            }), 201

    except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/waypoint-image", methods=["POST"])
def upload_waypoint_image():
    flight_id = request.form.get("flight_id")
    waypoint = request.form.get("waypoint")

    image = request.files.get("image")

    if not all([flight_id, waypoint, image]):
        return jsonify({"error": "Missing data"}), 400

    logs = load_logs()

    for log in logs:
        if log.get("id") == flight_id:
            for wp in log.get("waypoints", []):
                if wp.get("name") == waypoint:
                    wp.setdefault("images", [])
                    wp["images"].append(
                        f"/static/waypoint_images/{flight_id}/{waypoint}.jpg"
                    )

    save_dir = f"static/waypoint_images/{flight_id}"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{waypoint}_{int(datetime.now().timestamp())}.jpg"
    image.save(os.path.join(save_dir, filename))

    save_logs(logs)

    return jsonify({
        "message": "Waypoint image uploaded",
        "flight_id": flight_id,
        "waypoint": waypoint
    }), 200

@app.route("/debug-logs")
def debug_logs():
    return jsonify(load_logs())

from flask import send_from_directory

@app.route("/download/management-strategies")
def download_management_strategies():
    return send_from_directory(
        directory=os.path.join("static", "documents"),
        path="How to Keep Your Pineapples Healthy_ Local and International Management Tips.pdf",
        as_attachment=True
    )

# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run()