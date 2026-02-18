import cv2
import time
import os
import threading
import json
import datetime
import requests
from flask import Flask, Response, jsonify, send_from_directory, request
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIG ---
FRAME_WIDTH = 854
FRAME_HEIGHT = 480
FPS_LIMIT = 15          
AI_INTERVAL_SEC = 0.5   
HISTORY_FILE = "history.json"
PORTFOLIO_WEB_URL = "http://localhost:8090" # Source for Radar/KPI data

CLASS_NAMES = {
    0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK",
    14: "BIRD", 15: "CAT", 16: "DOG", 17: "HORSE", 18: "SHEEP", 19: "COW"
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# --- GLOBAL STATE ---
output_frame = None
lock = threading.Lock()

# --- PERSISTENT HISTORY MANAGER ---
class HistoryManager:
    def __init__(self):
        self.file = HISTORY_FILE
        self.total_count = 0
        self.load()

    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.total_count = data.get("total", 0)
            except:
                self.total_count = 0

    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({"total": self.total_count}, f)
        except:
            pass

    def increment(self, amount):
        if amount > 0:
            self.total_count += amount
            threading.Thread(target=self.save).start()

history = HistoryManager()
current_stats = {"status": "Online", "total_all_time": history.total_count}

# --- RADAR & BIG DATA PROXY ROUTES (Fixes 404s) ---
@app.route("/api/live")
def proxy_live():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/live", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"aircraft": {}})

@app.get("/api/kpi")
def proxy_kpi():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/kpi", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"unique": 0, "speed": "0 kts", "alt": "0 ft"})

@app.get("/api/history")
def proxy_history():
    range_type = request.args.get('range_type', '24h')
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/history?range_type={range_type}", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"labels": [], "data": []})

@app.get("/api/scatter")
def proxy_scatter():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/scatter", timeout=5)
        return jsonify(r.json())
    except:
        return jsonify([])

@app.get("/api/daily")
def proxy_daily():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/daily", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"labels": [], "data": []})

@app.get("/api/altitude")
def proxy_altitude():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/altitude", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"labels": [], "data": []})

@app.get("/api/direction")
def proxy_direction():
    try:
        r = requests.get(f"{PORTFOLIO_WEB_URL}/api/direction", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"data": [0]*8})

# --- UI SERVING ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# --- AI ENGINE ---
def start_engine():
    global output_frame, current_stats
    model = YOLO("yolov8n.pt") 
    user, pwd, ip = os.getenv('CAMERA_USER'), os.getenv('CAMERA_PASS'), os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    last_ai_time = 0
    last_boxes = [] 
    last_seen_counts = {}

    while True:
        success, frame = cap.read()
        if not success:
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            time.sleep(1)
            continue

        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        now = time.time()
        
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            results = model(draw_frame, classes=TARGET_CLASSES, verbose=False)
            raw_counts, temp_boxes = {}, []
            
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    label = CLASS_NAMES.get(cls_id, "Unknown")
                    temp_boxes.append((x1, y1, x2, y2, label))
                    raw_counts[label] = raw_counts.get(label, 0) + 1
            
            last_boxes = temp_boxes
            new_v = sum([max(0, raw_counts.get(l, 0) - last_seen_counts.get(l, 0)) for l in raw_counts])
            if new_v > 0: history.increment(new_v)
            last_seen_counts = raw_counts
            
            with lock:
                payload = {"status": "Online", "total_all_time": history.total_count}
                payload.update(raw_counts)
                if raw_counts:
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    payload['log'] = f"[{ts}] DETECTED: {', '.join([f'{k}: {v}' for k,v in raw_counts.items()])}"
                current_stats = payload

        for (x1, y1, x2, y2, label) in last_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(draw_frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        with lock:
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            output_frame = bytearray(encoded)
        time.sleep(0.01)

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            with lock:
                if output_frame:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
            time.sleep(1.0 / FPS_LIMIT)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock: return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=start_engine, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)