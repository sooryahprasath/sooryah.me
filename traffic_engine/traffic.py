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
FPS_LIMIT = 15                          
AI_INTERVAL_SEC = 0.05 
JPEG_QUALITY = 35       

# --- SOFTWARE COLOR CONTROL ---
CONTRAST_ALPHA = 1.1     
BRIGHTNESS_BETA = -40    

# --- BENGALURU TRAFFIC TUNING ---
AI_RESOLUTION = 640     
CONFIDENCE = 0.15 
CLASS_NAMES = {
    0: "Hatchback", 1: "Sedan", 2: "SUV", 3: "MUV", 4: "Bus", 
    5: "Truck", 6: "Three-wheeler", 7: "Two-wheeler", 8: "LCV", 
    9: "Mini-bus", 10: "Tempo-traveller", 11: "Bicycle", 12: "Van", 13: "Other",
    14: "Person" 
}

# --- IDLE LOGIC ---
last_access_time = 0 
IDLE_TIMEOUT = 60 

HISTORY_FILE = "history.json"
MODEL_PATH = "best.pt" 

lock = threading.Lock()

# --- STANDBY FRAME FOR MOBILE BROWSERS ---
# This prevents the stream from timing out while the AI loads
standby_img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8)
cv2.putText(standby_img, "VM Waking Up... Connecting to RTSP...", (100, FRAME_HEIGHT//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
_, standby_encoded = cv2.imencode('.jpg', standby_img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
STANDBY_FRAME = bytearray(standby_encoded)

output_frame = STANDBY_FRAME

# --- GLOBAL STATE ---
latest_frame_for_ai = None
boxes_to_draw = []
ai_lock = threading.Lock()
ai_worker_started = False 

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

class OnDemandCamera:
    """Connects to the RTSP stream ONLY when someone is on the site"""
    def __init__(self, src):
        self.src = src
        self.cap = None
        self.frame = None
        self.read_lock = threading.Lock()
        self.is_running = False
        self.thread = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.thread = threading.Thread(target=self.update, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        with self.read_lock:
            self.frame = None

    def update(self):
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)
                continue
            grabbed, frame = self.cap.read()
            if not grabbed:
                self.cap.release()
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            with self.read_lock:
                self.frame = frame

    def read(self):
        with self.read_lock:
            return self.frame is not None, self.frame.copy() if self.frame is not None else None

def ai_worker():
    global latest_frame_for_ai, boxes_to_draw, current_stats, history, last_access_time, ai_worker_started
    if ai_worker_started: return
    ai_worker_started = True

    try:
        model = YOLO(MODEL_PATH)
        print(f"✅ AI Tracking Online using {MODEL_PATH}")
    except Exception as e:
        print(f"❌ Model error: {e}")
        return

    previous_ids = set()

    while True:
        if (time.time() - last_access_time) > IDLE_TIMEOUT:
            with ai_lock:
                boxes_to_draw = []
                current_stats["status"] = "AI Idle (Saving Resources)"
            time.sleep(1.0)
            continue

        with ai_lock:
            frame_to_process = latest_frame_for_ai.copy() if latest_frame_for_ai is not None else None

        if frame_to_process is None:
            time.sleep(0.01)
            continue

        try:
            results = model.track(
                frame_to_process, 
                persist=True, 
                classes=list(CLASS_NAMES.keys()), 
                conf=CONFIDENCE, 
                imgsz=AI_RESOLUTION, 
                verbose=False,
                agnostic_nms=True,
                tracker="bytetrack.yaml" 
            )

            current_raw_counts = {}
            new_boxes = []
            current_ids = set()

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                clss = results[0].boxes.cls.cpu().numpy().astype(int)

                for box, obj_id, cls in zip(boxes, ids, clss):
                    label = CLASS_NAMES.get(cls, "Unknown")
                    new_boxes.append((*box, f"{label} #{obj_id}"))
                    current_raw_counts[label] = current_raw_counts.get(label, 0) + 1
                    current_ids.add(obj_id)

            newly_detected_objects = current_ids - previous_ids
            if len(newly_detected_objects) > 0:
                history.increment(len(newly_detected_objects))
            
            previous_ids = current_ids

            with ai_lock:
                boxes_to_draw = new_boxes
                current_stats = {
                    "status": "AI Live (Tracking)", 
                    "total_all_time": history.total_count, 
                    **current_raw_counts
                }
        except Exception:
            pass

        time.sleep(AI_INTERVAL_SEC)

def start_engine():
    global output_frame, latest_frame_for_ai, boxes_to_draw
    rtsp_url = "rtsp://127.0.0.1:8554/video_feed"
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    # Do not start camera immediately. Let OnDemand logic handle it.
    cam = OnDemandCamera(rtsp_url)
    threading.Thread(target=ai_worker, daemon=True).start()

    while True:
        is_active = (time.time() - last_access_time) < IDLE_TIMEOUT
        
        # IDLE: Stop camera, release network, reset to Standby frame
        if not is_active:
            cam.stop()
            with lock:
                output_frame = STANDBY_FRAME
            time.sleep(1.0)
            continue

        # ACTIVE: Start camera (only initializes if not running)
        cam.start()

        success, frame = cam.read()
        if not success or frame is None:
            time.sleep(0.01)
            continue

        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        draw_frame = cv2.convertScaleAbs(draw_frame, alpha=CONTRAST_ALPHA, beta=BRIGHTNESS_BETA)

        with ai_lock:
            latest_frame_for_ai = draw_frame.copy()
            current_boxes = boxes_to_draw.copy()

        for (x1, y1, x2, y2, label) in current_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(draw_frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        with lock:
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            output_frame = bytearray(encoded)
        
        time.sleep(0.01)

@app.route("/video_feed")
def video_feed():
    global last_access_time
    last_access_time = time.time()
    
    def generate():
        global last_access_time
        # Instantly send the standby frame so mobile browsers don't timeout the connection
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + STANDBY_FRAME + b'\r\n')
        
        while True:
            last_access_time = time.time() 
            with lock:
                frame_to_send = output_frame
                
            if frame_to_send: 
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_to_send + b'\r\n')
            time.sleep(1.0 / FPS_LIMIT)
            
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    global last_access_time
    last_access_time = time.time()
    with lock: return jsonify(current_stats)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)