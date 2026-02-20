import cv2
import time
import os
import threading
import json
import datetime
import numpy as np
from flask import Flask, Response, jsonify
from flask_cors import CORS
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# CONFIG - MAXIMUM RESOLUTION (3K)
# Note: 3K is typically 3072 x 1728
FRAME_WIDTH, FRAME_HEIGHT = 3072, 1728 
FPS_LIMIT = 8           # Reduced FPS to keep CPU from overheating at 3K
AI_INTERVAL_SEC = 3.0    # Check AI every 3 seconds to give the CPU a rest
HISTORY_FILE = "history.json"
CLASS_NAMES = {0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK"}

# GLOBAL STATE
output_frame = cv2.imencode('.jpg', np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8))[1].tobytes()
lock = threading.Lock()

class HistoryManager:
    def __init__(self):
        self.file = HISTORY_FILE
        self.total_count = 0
        self.load()
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.total_count = json.load(f).get("total", 0)
            except: self.total_count = 0
    def save(self):
        with open(self.file, 'w') as f: json.dump({"total": self.total_count}, f)
    def increment(self, amount):
        if amount > 0:
            self.total_count += amount
            threading.Thread(target=self.save).start()

history = HistoryManager()
current_stats = {"status": "Starting", "total_all_time": history.total_count}

def start_engine():
    global output_frame, current_stats
    try:
        # Load the smallest model to maximize speed at high res
        model = YOLO("yolov8n.pt") 
    except: return

    user, pwd, ip = os.getenv('CAMERA_USER'), os.getenv('CAMERA_PASS'), os.getenv('CAMERA_IP')
    
    # 3K URL - Ensure channel and subtype are correct for your camera's high-res stream
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif"
    
    # CRITICAL: Force TCP to handle the massive 3K data stream without corruption
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Force latest frame only
    
    last_ai_time = 0
    previous_raw_counts = {} 
    last_valid_counts = {}   
    temp_boxes = []

    while True:
        success, frame = cap.read()
        if not success:
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            continue

        # Resize to full 3K for display
        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        now = time.time()
        
        # AI INFERENCE
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            try:
                # OPTIMIZATION: Even though video is 3K, AI only looks at a 640px version.
                # This keeps the CPU load manageable.
                results = model(draw_frame, classes=list(CLASS_NAMES.keys()), verbose=False, imgsz=640)
                current_raw_counts = {}
                new_boxes = []
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = CLASS_NAMES.get(int(box.cls[0]), "Unknown")
                        new_boxes.append((x1, y1, x2, y2, label))
                        current_raw_counts[label] = current_raw_counts.get(label, 0) + 1
                
                temp_boxes = new_boxes
                
                # Debounce logic
                smoothed_counts = {}
                all_keys = set(current_raw_counts.keys()) | set(previous_raw_counts.keys())
                for label in all_keys:
                    smoothed_counts[label] = max(current_raw_counts.get(label, 0), previous_raw_counts.get(label, 0))

                new_v = sum([max(0, smoothed_counts.get(l, 0) - last_valid_counts.get(l, 0)) for l in smoothed_counts])
                if new_v > 0: history.increment(new_v)
                
                previous_raw_counts = current_raw_counts 
                last_valid_counts = smoothed_counts      
                
                with lock:
                    current_stats = {"status": "Online (3K Mode)", "total_all_time": history.total_count, **current_raw_counts}
                    if current_raw_counts:
                        ts = datetime.datetime.now().strftime("%H:%M:%S")
                        current_stats['log'] = f"[{ts}] DETECTED: {current_raw_counts}"
            except: pass

        # Draw Labels (Large scale for 3K)
        for (x1, y1, x2, y2, label) in temp_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 6) # Thicker lines
            cv2.putText(draw_frame, label, (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)

        with lock:
            # Compression quality 50 - Lowered for 3K to avoid lagging the browser
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            output_frame = bytearray(encoded)
        
        # CPU BREATHING ROOM
        time.sleep(0.01)

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            with lock:
                if output_frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
            # The browser can only handle so much 3K data; we cap it at our set FPS
            time.sleep(1.0 / FPS_LIMIT)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock: return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=start_engine, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)