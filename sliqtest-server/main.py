from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from datetime import datetime, timezone
import json
import threading
import os

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "leaderboard.json"

DATA_DIR.mkdir(exist_ok=True)

lock = threading.Lock()

DEFAULT_DATA = {
    "cps": [],
    "reaction": []
}


def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return DEFAULT_DATA.copy()

        data.setdefault("cps", [])
        data.setdefault("reaction", [])

        return data

    except Exception:
        return DEFAULT_DATA.copy()


def save_data(data):
    temp_file = DATA_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.replace(temp_file, DATA_FILE)


def clean_username(username):
    if not isinstance(username, str):
        return "Player"

    username = username.strip()

    if not username:
        return "Player"

    return username[:32]


def add_result(category, username, value):
    username = clean_username(username)

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if value <= 0:
        return None

    result = {
        "username": username,
        "value": round(value, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with lock:
        data = load_data()

        data[category].append(result)

        # Keep server storage reasonably small.
        # The leaderboard only needs the best results.
        data[category] = sorted(
            data[category],
            key=lambda x: x["value"],
            reverse=(category == "cps")
        )[:1000]

        save_data(data)

    return result


@app.get("/")
def index():
    return jsonify({
        "name": "SliqTest Server",
        "status": "online",
        "version": "1.0.0"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "server": "SliqTest",
        "time": datetime.now(timezone.utc).isoformat()
    })


@app.get("/api/leaderboard")
def leaderboard():
    with lock:
        data = load_data()

    cps = sorted(
        data["cps"],
        key=lambda x: x["value"],
        reverse=True
    )[:3]

    reaction = sorted(
        data["reaction"],
        key=lambda x: x["value"]
    )[:3]

    return jsonify({
        "cps": cps,
        "reaction": reaction
    })


@app.get("/api/results")
def results():
    with lock:
        data = load_data()

    return jsonify(data)


@app.post("/api/cps")
def submit_cps():
    body = request.get_json(silent=True) or {}

    username = body.get("username", "Player")
    value = body.get("cps")

    # Client must only send valid results.
    result = add_result("cps", username, value)

    if result is None:
        return jsonify({
            "success": False,
            "error": "Invalid CPS result"
        }), 400

    return jsonify({
        "success": True,
        "result": result
    })


@app.post("/api/reaction")
def submit_reaction():
    body = request.get_json(silent=True) or {}

    username = body.get("username", "Player")
    value = body.get("reaction_ms")

    result = add_result("reaction", username, value)

    if result is None:
        return jsonify({
            "success": False,
            "error": "Invalid reaction result"
        }), 400

    return jsonify({
        "success": True,
        "result": result
    })


@app.post("/api/result")
def submit_result():
    body = request.get_json(silent=True) or {}

    username = body.get("username", "Player")
    test_type = body.get("type")

    if test_type == "cps":
        value = body.get("value")
        result = add_result("cps", username, value)

    elif test_type == "reaction":
        value = body.get("value")
        result = add_result("reaction", username, value)

    else:
        return jsonify({
            "success": False,
            "error": "Unknown test type"
        }), 400

    if result is None:
        return jsonify({
            "success": False,
            "error": "Invalid result"
        }), 400

    return jsonify({
        "success": True,
        "result": result
    })


if __name__ == "__main__":
    print("")
    print("========================================")
    print(" SLIQTEST SERVER")
    print("========================================")
    print("Local address: http://127.0.0.1:5000")
    print("Health check:  http://127.0.0.1:5000/health")
    print("Leaderboard:    http://127.0.0.1:5000/api/leaderboard")
    print("========================================")
    print("")

    try:
        from waitress import serve

        print("Starting with Waitress...")
        serve(app, host="0.0.0.0", port=5000)

    except ImportError:
        print("Waitress unavailable. Starting Flask development server...")
        app.run(host="0.0.0.0", port=5000)
