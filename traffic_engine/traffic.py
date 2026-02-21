import cv2
import time
import os
import threading
import json
import numpy as np
from flask import Flask, Response, jsonify
from flask_cors import CORS
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
FRAME_WIDTH, FRAME_HEIGHT = 1920, 1080  
FPS_LIMIT = 15                          
AI_INTERVAL_SEC = 0.05 
JPEG_QUALITY = 35       
CONTRAST_ALPHA = 1.1     
BRIGHTNESS_BETA = -40    
AI_RESOLUTION = 640     
CONFIDENCE = 0.15 
CLASS_NAMES = {
    0: "Hatchback", 1: "Sedan", 2: "SUV", 3: "MUV", 4: "Bus", 
    5: "Truck", 6: "Three-wheeler", 7: "Two-wheeler", 8: "LCV", 
    9: "Mini-bus", 10: "Tempo-traveller", 11: "Bicycle", 12: "Van", 13: "Other",
    14: "Person" 
}
IDLE_TIMEOUT = 60 
HISTORY_FILE = "/app/history.json"
MODEL_PATH = "/app/best.pt" 

lock = threading.Lock()
ai_lock = threading.Lock()

# --- STATE ---
last_access_time = 0 
latest_frame_for_ai = None
boxes_to_draw = []
ai_worker_started = False 

# Standby Frame
standby_img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8)
cv2.putText(standby_img, "VM Waking Up... Connecting to RTSP...", (100, FRAME_HEIGHT//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
_, standby_encoded = cv2.imencode('.jpg', standby_img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
STANDBY_FRAME = bytearray(standby_encoded)
output_frame = STANDBY_FRAME

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

# --- UPDATED OnDemandCamera ---
class OnDemandCamera:
    def __init__(self, src):
        self.src = src
        self.cap = None
        self.frame = None
        self.read_lock = threading.Lock()
        self.is_running = False
        self.thread = None
        self.last_frame_time = time.time() # Watchdog timer

    def start(self):
        if not self.is_running:
            print("📷 [CAMERA] Starting RTSP connection...")
            self.is_running = True
            # Tuned FFMPEG options to fail fast instead of hanging forever
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|threads;2"
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.last_frame_time = time.time()
                self.thread = threading.Thread(target=self.update, daemon=True)
                self.thread.start()
                print("📷 [CAMERA] Connected successfully.")
            else:
                print("❌ [CAMERA] Failed to open stream.")
                self.is_running = False

    def stop(self):
        if self.is_running:
            print("📷 [CAMERA] Stopping connection...")
            self.is_running = False
            # Don't join the thread here, let it die naturally to prevent blocking
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
            self.cap = None
            with self.read_lock:
                self.frame = None

    def update(self):
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                break
            
            grabbed, frame = self.cap.read()
            if not grabbed:
                print("⚠️ [CAMERA] Dropped frame or empty buffer.")
                time.sleep(0.5)
                continue
            
            with self.read_lock:
                self.frame = frame
                self.last_frame_time = time.time()

        print("📷 [CAMERA] Update thread exiting.")
        self.is_running = False

    def read(self):
        with self.read_lock:
            # Watchdog: If we haven't received a frame in 5 seconds, assume dead
            if self.is_running and (time.time() - self.last_frame_time > 5):
                 print("🚨 [CAMERA] Watchdog tripped! Stream is frozen.")
                 self.is_running = False # Force a restart on the next loop
                 return False, None
            
            return self.frame is not None, self.frame.copy() if self.frame is not None else None


def ai_worker():
    global latest_frame_for_ai, boxes_to_draw, current_stats, history, last_access_time, ai_worker_started
    if ai_worker_started: return
    ai_worker_started = True
    print("🧠 [AI] Worker thread started.")
    
    # Initialize YOLO only once
    model = YOLO(MODEL_PATH)
    previous_ids = set()

    while True:
        # Check Idle State
        if (time.time() - last_access_time) > IDLE_TIMEOUT:
            with ai_lock: 
                boxes_to_draw = []
                current_stats["status"] = "Idling"
            time.sleep(1)
            continue
            
        with ai_lock: 
            frame = latest_frame_for_ai.copy() if latest_frame_for_ai is not None else None
            
        if frame is None:
            time.sleep(0.1)
            continue
            
        try:
            results = model.track(frame, persist=True, conf=CONFIDENCE, imgsz=AI_RESOLUTION, verbose=False)
            new_boxes = []
            current_ids = set()
            counts = {}
            
            if results[0].boxes.id is not None:
                for box, obj_id, cls in zip(results[0].boxes.xyxy.cpu().numpy().astype(int), 
                                            results[0].boxes.id.cpu().numpy().astype(int), 
                                            results[0].boxes.cls.cpu().numpy().astype(int)):
                    lbl = CLASS_NAMES.get(cls, "Object")
                    new_boxes.append((*box, f"{lbl} #{obj_id}"))
                    counts[lbl] = counts.get(lbl, 0) + 1
                    current_ids.add(obj_id)
                    
            # Update history only for newly tracked objects
            new_objects_count = len(current_ids - previous_ids)
            if new_objects_count > 0:
                history.increment(new_objects_count)
            previous_ids = current_ids
            
            with ai_lock:
                boxes_to_draw = new_boxes
                current_stats = {"status": "AI Live", "total_all_time": history.total_count, **counts}
                
        except Exception as e:
            print(f"⚠️ [AI] Inference error: {e}")
            
        time.sleep(AI_INTERVAL_SEC)

# --- UPDATED Engine Loop ---
def engine_loop():
    global output_frame, latest_frame_for_ai
    print("⚙️ [ENGINE] Main engine loop starting.")
    cam = OnDemandCamera("rtsp://127.0.0.1:8554/video_feed")
    threading.Thread(target=ai_worker, daemon=True).start()
    
    while True:
        is_idle = (time.time() - last_access_time) > IDLE_TIMEOUT
        
        if is_idle:
            if cam.is_running:
                cam.stop()
            with lock: 
                output_frame = STANDBY_FRAME
            with ai_lock:
                latest_frame_for_ai = None # Clear the old frame so AI stops looping it
            time.sleep(1)
            continue
            
        # If not idle, ensure camera is running
        if not cam.is_running:
            cam.start()
            
        success, frame = cam.read()
        
        if not success:
            # Show a reconnecting frame if stream dropped mid-session
            error_img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8)
            cv2.putText(error_img, "Stream Dropped. Reconnecting...", (100, FRAME_HEIGHT//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            _, err_encoded = cv2.imencode('.jpg', error_img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            with lock:
                output_frame = bytearray(err_encoded)
            time.sleep(0.5)
            continue

        # Valid frame received, process it
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        frame = cv2.convertScaleAbs(frame, alpha=CONTRAST_ALPHA, beta=BRIGHTNESS_BETA)
        
        # Give a copy to the AI
        with ai_lock:
            latest_frame_for_ai = frame.copy()
            cur_boxes = boxes_to_draw.copy()
            
        # Draw boxes on the broadcast frame
        for (x1, y1, x2, y2, label) in cur_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        # Encode and set for broadcast
        with lock:
            _, en = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            output_frame = bytearray(en)
            
        time.sleep(0.01)

@app.route("/video_feed")
def video_feed():
    global last_access_time
    last_access_time = time.time()
    # Let the client know the ping was received
    
    def gen():
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + STANDBY_FRAME + b'\r\n')
        while True:
            # Update access time constantly while reading stream
            global last_access_time
            last_access_time = time.time() 
            
            with lock: 
                frame = output_frame
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1.0 / FPS_LIMIT)
            
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    global last_access_time
    last_access_time = time.time() # Calling stats also keeps the server awake
    return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=engine_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)