import cv2
import time
import os
import threading
import json
import datetime
from flask import Flask, Response, jsonify
from flask_cors import CORS  # Required to allow port 8090 to talk to 5000
from ultralytics import YOLO

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing to allow your main dashboard to fetch stats
CORS(app) 

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
            # Save history in a background thread to prevent engine stutter
            threading.Thread(target=self.save).start()

history = HistoryManager()
current_stats = {"status": "Online", "total_all_time": history.total_count}

# --- AI ENGINE ---
def start_engine():
    global output_frame, current_stats
    
    print("🚀 Loading AI Model...")
    model = YOLO("yolov8n.pt") 
    
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    last_ai_time = 0
    last_boxes = [] 
    last_seen_counts = {}

    print("✅ Engine Started. Processing stream...")

    while True:
        success, frame = cap.read()
        if not success:
            print("⚠️ Stream lost. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        # Resize for consistent processing speed
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
            # Logic: Only increment the total when a new vehicle enters the frame
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

        # Draw detections on the frame for the MJPEG stream
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
    # Independent endpoint for traffic statistics
    with lock:
        return jsonify(current_stats)

if __name__ == "__main__":
    t = threading.Thread(target=start_engine, daemon=True)
    t.start()
    # Explicitly listening on 0.0.0.0 for external network access
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)