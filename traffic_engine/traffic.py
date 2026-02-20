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

# --- PERFORMANCE & COMPRESSION ---
FRAME_WIDTH, FRAME_HEIGHT = 1920, 1080  
FPS_LIMIT = 12                          
AI_INTERVAL_SEC = 1.0                    
JPEG_QUALITY = 35       

# --- SOFTWARE COLOR CONTROL ---
CONTRAST_ALPHA = 1.1     
BRIGHTNESS_BETA = -40    

# --- BENGALURU TRAFFIC TUNING ---
AI_RESOLUTION = 640     
CONFIDENCE = 0.25
# Updated to 15 classes including the new 'Person' class
CLASS_NAMES = {
    0: "Hatchback", 1: "Sedan", 2: "SUV", 3: "MUV", 4: "Bus", 
    5: "Truck", 6: "Three-wheeler", 7: "Two-wheeler", 8: "LCV", 
    9: "Mini-bus", 10: "Tempo-traveller", 11: "Bicycle", 12: "Van", 13: "Other",
    14: "Person" 
}

# --- IDLE LOGIC CONFIG ---
last_access_time = 0 
IDLE_TIMEOUT = 60 # Seconds until AI sleeps to save VM resources

HISTORY_FILE = "history.json"
MODEL_PATH = "best.pt" # Ensure this file is in your traffic_engine folder

output_frame = cv2.imencode('.jpg', np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8))[1].tobytes()
lock = threading.Lock()

# --- GLOBAL STATE FOR ASYNC AI ---
latest_frame_for_ai = None
boxes_to_draw = []
ai_lock = threading.Lock()

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

class ThreadedCamera:
    def __init__(self, src):
        self.src = src
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()

    def start(self):
        if self.started: return None
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            grabbed, frame = self.cap.read()
            if not grabbed:
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame

    def read(self):
        with self.read_lock:
            frame = self.frame.copy() if self.frame is not None else None
            return self.grabbed, frame

    def stop(self):
        self.started = False
        self.thread.join()
        self.cap.release()

# --- BACKGROUND AI THREAD ---
def ai_worker():
    global latest_frame_for_ai, boxes_to_draw, current_stats, history, last_access_time
    try:
        model = YOLO(MODEL_PATH) 
        print(f"✅ Loaded Bengaluru Traffic weights from {MODEL_PATH}")
    except Exception as e:
        print(f"❌ Model error: {e}")
        return

    previous_raw_counts = {} 
    last_valid_counts = {}   

    while True:
        # IDLE CHECK: If no request in IDLE_TIMEOUT, skip inference
        if (time.time() - last_access_time) > IDLE_TIMEOUT:
            with ai_lock:
                boxes_to_draw = []
                current_stats["status"] = "AI Idle (Saving Resources)"
            time.sleep(2) # Deep sleep while idle
            continue

        with ai_lock:
            frame_to_process = latest_frame_for_ai.copy() if latest_frame_for_ai is not None else None

        if frame_to_process is None:
            time.sleep(0.1)
            continue

        try:
            results = model(frame_to_process, classes=list(CLASS_NAMES.keys()), verbose=False, imgsz=AI_RESOLUTION, conf=CONFIDENCE)
            current_raw_counts = {}
            new_boxes = []
            
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = CLASS_NAMES.get(int(box.cls[0]), "Unknown")
                    new_boxes.append((x1, y1, x2, y2, label))
                    current_raw_counts[label] = current_raw_counts.get(label, 0) + 1
            
            smoothed_counts = {}
            all_keys = set(current_raw_counts.keys()) | set(previous_raw_counts.keys())
            for label in all_keys:
                smoothed_counts[label] = max(current_raw_counts.get(label, 0), previous_raw_counts.get(label, 0))

            new_v = sum([max(0, smoothed_counts.get(l, 0) - last_valid_counts.get(l, 0)) for l in smoothed_counts])
            if new_v > 0: history.increment(new_v)
            
            previous_raw_counts = current_raw_counts 
            last_valid_counts = smoothed_counts      
            
            with ai_lock:
                boxes_to_draw = new_boxes
                current_stats = {"status": "AI Live (Processing)", "total_all_time": history.total_count, **current_raw_counts}
                if current_raw_counts:
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    current_stats['log'] = f"[{ts}] DETECTED: {current_raw_counts}"
        except Exception as e:
            print(f"AI Processing Error: {e}")

        time.sleep(AI_INTERVAL_SEC)

# --- MAIN VIDEO STREAM THREAD ---
def start_engine():
    global output_frame, latest_frame_for_ai, boxes_to_draw
    
    rtsp_url = "rtsp://127.0.0.1:8554/video_feed"
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    cam = ThreadedCamera(rtsp_url).start()
    threading.Thread(target=ai_worker, daemon=True).start()

    while True:
        success, frame = cam.read()
        if not success or frame is None:
            time.sleep(0.05)
            continue

        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        draw_frame = cv2.convertScaleAbs(draw_frame, alpha=CONTRAST_ALPHA, beta=BRIGHTNESS_BETA)

        with ai_lock:
            latest_frame_for_ai = draw_frame.copy()
            current_boxes = boxes_to_draw.copy()

        for (x1, y1, x2, y2, label) in current_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(draw_frame, label, (x1, y1-15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        with lock:
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            output_frame = bytearray(encoded)
        
        time.sleep(0.02)

@app.route("/video_feed")
def video_feed():
    global last_access_time
    last_access_time = time.time() # Wake up AI on feed request
    def generate():
        while True:
            with lock:
                if output_frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
            time.sleep(1.0 / FPS_LIMIT)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    global last_access_time
    last_access_time = time.time() # Wake up AI on API request
    with lock: return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=start_engine, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)