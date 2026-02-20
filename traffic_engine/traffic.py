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

# --- 1. PERFORMANCE & COMPRESSION ---
FRAME_WIDTH, FRAME_HEIGHT = 1920, 1080  
FPS_LIMIT = 12                          
AI_INTERVAL_SEC = 1.0                   
JPEG_QUALITY = 35       # Highly compressed to stop the network/Flask stutter

# --- 2. SOFTWARE COLOR CONTROL ---
CONTRAST_ALPHA = 1.1    # Slight contrast bump
BRIGHTNESS_BETA = -40   # Aggressively darken the image to kill the sun glare

# --- 3. TRAFFIC TUNING ---
AI_RESOLUTION = 640    
CONFIDENCE = 0.20      
CLASS_NAMES = {0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK"}

HISTORY_FILE = "history.json"

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

def start_engine():
    global output_frame, current_stats
    try:
        # UPGRADED AI: Using the 'Small' model instead of 'Nano' for better recognition
        model = YOLO("yolov8s.pt") 
    except Exception as e:
        print(f"Model error: {e}")
        return

    user, pwd, ip = os.getenv('CAMERA_USER'), os.getenv('CAMERA_PASS'), os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif"
    
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    cam = ThreadedCamera(rtsp_url).start()
    
    last_ai_time = 0
    previous_raw_counts = {} 
    last_valid_counts = {}   
    temp_boxes = []

    while True:
        success, frame = cam.read()
        if not success or frame is None:
            time.sleep(0.05)
            continue

        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # Apply Digital Sunglasses
        draw_frame = cv2.convertScaleAbs(draw_frame, alpha=CONTRAST_ALPHA, beta=BRIGHTNESS_BETA)

        now = time.time()
        
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            try:
                results = model(draw_frame, classes=list(CLASS_NAMES.keys()), verbose=False, imgsz=AI_RESOLUTION, conf=CONFIDENCE)
                current_raw_counts = {}
                new_boxes = []
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = CLASS_NAMES.get(int(box.cls[0]), "Unknown")
                        new_boxes.append((x1, y1, x2, y2, label))
                        current_raw_counts[label] = current_raw_counts.get(label, 0) + 1
                
                temp_boxes = new_boxes
                
                smoothed_counts = {}
                all_keys = set(current_raw_counts.keys()) | set(previous_raw_counts.keys())
                for label in all_keys:
                    smoothed_counts[label] = max(current_raw_counts.get(label, 0), previous_raw_counts.get(label, 0))

                new_v = sum([max(0, smoothed_counts.get(l, 0) - last_valid_counts.get(l, 0)) for l in smoothed_counts])
                if new_v > 0: history.increment(new_v)
                
                previous_raw_counts = current_raw_counts 
                last_valid_counts = smoothed_counts      
                
                with lock:
                    current_stats = {"status": "YOLOv8s Running", "total_all_time": history.total_count, **current_raw_counts}
                    if current_raw_counts:
                        ts = datetime.datetime.now().strftime("%H:%M:%S")
                        current_stats['log'] = f"[{ts}] DETECTED: {current_raw_counts}"
            except: pass

        for (x1, y1, x2, y2, label) in temp_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(draw_frame, label, (x1, y1-15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        with lock:
            # Apply maximum compression
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            output_frame = bytearray(encoded)
        
        time.sleep(0.05)

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            with lock:
                if output_frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
            time.sleep(1.0 / FPS_LIMIT)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock: return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=start_engine, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)