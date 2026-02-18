import cv2
import time
import os
import threading
import json
import datetime
from flask import Flask, Response, jsonify, send_from_directory
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIG ---
FRAME_WIDTH = 854
FRAME_HEIGHT = 480
FPS_LIMIT = 15          
AI_INTERVAL_SEC = 0.5   
HISTORY_FILE = "history.json"

CLASS_NAMES = {
    0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK",
    14: "BIRD", 15: "CAT", 16: "DOG", 17: "HORSE", 18: "SHEEP", 19: "COW"
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# --- PERSISTENT HISTORY (Non-Blocking) ---
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

# --- GLOBAL STATE ---
output_frame = None
# Initialize with history so the dashboard isn't empty on first load
current_stats = {"status": "Online", "total_all_time": history.total_count}
lock = threading.Lock()

# --- CAMERA CLASS (Auto-Healing) ---
class RobustCamera:
    def __init__(self, src):
        self.src = src
        self.cap = None
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                print("📷 Connecting to camera...")
                self.cap = cv2.VideoCapture(self.src)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                time.sleep(1)
                
                if not self.cap.isOpened():
                    print("❌ Connection failed. Retrying in 5s...")
                    time.sleep(5)
                    continue

            success, frame = self.cap.read()
            if success:
                with self.lock:
                    self.frame = frame
                time.sleep(1.0 / FPS_LIMIT)
            else:
                print("⚠️ Lost stream signal. Reconnecting...")
                if self.cap: self.cap.release()
                time.sleep(1)

    def get_frame(self):
        with self.lock:
            return self.frame

# --- UI ROUTES (Serves Dashboard & Assets) ---
@app.route('/')
def index():
    # Serves the index.html from the same directory as this script
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    # Serves scripts/styles from the /static subfolder
    return send_from_directory('static', path)

# --- MAIN ENGINE ---
def start_engine():
    global output_frame, current_stats
    
    print("🚀 Loading AI Model...")
    model = YOLO("yolov8n.pt") 
    
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cam = RobustCamera(rtsp_url)
    last_ai_time = 0
    last_boxes = [] 
    last_seen_counts = {} 

    print("✅ Engine Started. Waiting for video...")

    while True:
        frame = cam.get_frame()
        
        if frame is None:
            time.sleep(0.1)
            continue

        # Resize for consistent AI and drawing
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        now = time.time()
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            try:
                results = model(frame, classes=TARGET_CLASSES, verbose=False)
                
                raw_counts = {}
                temp_boxes = []
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls_id = int(box.cls[0])
                        label = CLASS_NAMES.get(cls_id, "Unknown")
                        
                        temp_boxes.append((x1, y1, x2, y2, label))
                        raw_counts[label] = raw_counts.get(label, 0) + 1
                
                last_boxes = temp_boxes
                
                # --- LOGIC: COUNT NEW VEHICLES ---
                new_vehicles = 0
                for label, count in raw_counts.items():
                    prev = last_seen_counts.get(label, 0)
                    if count > prev:
                        new_vehicles += (count - prev)
                
                if new_vehicles > 0:
                    history.increment(new_vehicles)
                
                last_seen_counts = raw_counts
                
                # Update Global Stats for API (Always include critical keys)
                with lock:
                    payload = {"status": "Online", "total_all_time": history.total_count}
                    payload.update(raw_counts)
                    
                    if raw_counts:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        details = ", ".join([f"{k}: {v}" for k,v in raw_counts.items()])
                        payload['log'] = f"[{timestamp}] DETECTED: {details}"
                    elif 'log' in current_stats:
                        payload['log'] = current_stats['log'] # Keep last log visible
                    
                    current_stats = payload
                    
            except Exception as e:
                print(f"AI Error: {e}")

        # --- DRAWING ---
        for (x1, y1, x2, y2, label) in last_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # --- ENCODING ---
        with lock:
            (_, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            output_frame = bytearray(encodedImage)
        
        time.sleep(0.01)

def generate():
    while True:
        with lock:
            if output_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        time.sleep(1.0 / FPS_LIMIT)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify(current_stats)

if __name__ == "__main__":
    t = threading.Thread(target=start_engine, daemon=True)
    t.start()
    # Runs on port 5000, consistent with your Cloudflare Tunnel
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

import requests # Ensure this is at the top of traffic.py

# --- RADAR PROXY ROUTES ---
@app.route("/api/live")
def proxy_live():
    # Points to your main portfolio's live API
    r = requests.get("http://localhost:8090/api/live")
    return jsonify(r.json())

@app.route("/api/kpi")
def proxy_kpi():
    r = requests.get("http://localhost:8090/api/kpi")
    return jsonify(r.json())

# Add any other missing routes (daily, history, etc.) similarly