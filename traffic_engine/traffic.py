import cv2
import time
import os
import threading
import json
import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
FRAME_WIDTH, FRAME_HEIGHT = 1920, 1080  
FPS_LIMIT = 15                          
AI_INTERVAL_SEC = 0.05 
JPEG_QUALITY = 35       
# Set contrast and brightness to neutral so CLAHE can do the heavy lifting
CONTRAST_ALPHA = 1.0     
BRIGHTNESS_BETA = 0      
AI_RESOLUTION = 800     # Increased resolution for better detection at distance
CONFIDENCE = 0.15 
CLASS_NAMES = {
    0: "Hatchback", 1: "Sedan", 2: "SUV", 3: "MUV", 4: "Bus", 
    5: "Truck", 6: "Three-wheeler", 7: "Two-wheeler", 8: "LCV", 
    9: "Mini-bus", 10: "Tempo-traveller", 11: "Bicycle", 12: "Van", 13: "Other",
    14: "Person" 
}
IDLE_TIMEOUT = 60 
HISTORY_FILE = "/app/history.json"
# 🚀 UPGRADE: Pointing directly to the newly compiled OpenVINO model folder
MODEL_PATH = "/app/uvh_26_blr_8k_openvino_model" 

lock = threading.Lock()
ai_lock = threading.Lock()

# --- STATE ---
last_access_time = 0 
latest_frame_for_ai = None
new_frame_available = False 
boxes_to_draw = []
ai_worker_started = False 
active_viewers = 0 

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

class OnDemandCamera:
    def __init__(self, src):
        self.src = src
        self.cap = None
        self.frame = None
        self.read_lock = threading.Lock()
        self.is_running = False
        self.thread = None
        self.last_frame_time = time.time()

    def start(self):
        if not self.is_running:
            print("📷 [CAMERA] Starting RTSP connection...")
            self.is_running = True
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|stimeout;2000000|threads;2"
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
            print("📷 [CAMERA] Stop requested...")
            self.is_running = False 
            time.sleep(0.2) 
            if self.cap:
                try:
                    self.cap.release()
                    print("📷 [CAMERA] Resource released.")
                except Exception as e:
                    print(f"⚠️ [CAMERA] Error releasing: {e}")
            self.cap = None
            with self.read_lock:
                self.frame = None

    def update(self):
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                break
            
            if not self.cap.grab():
                time.sleep(0.1) 
                continue
                
            ret, frame = self.cap.retrieve()
            if ret:
                with self.read_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
        print("📷 [CAMERA] Update thread exiting cleanly.")

    def read(self):
        with self.read_lock:
            if self.is_running and (time.time() - self.last_frame_time > 5):
                 print("🚨 [CAMERA] Watchdog tripped! Stream is frozen.")
                 self.is_running = False 
                 return False, None
            return self.frame is not None, self.frame.copy() if self.frame is not None else None


def ai_worker():
    global latest_frame_for_ai, new_frame_available, boxes_to_draw, current_stats, history, last_access_time, ai_worker_started
    if ai_worker_started: return
    ai_worker_started = True
    print("🧠 [AI] Worker thread started. Using ByteTrack algorithm.")
    
    model = YOLO(MODEL_PATH)
    previous_ids = set()

    while True:
        if active_viewers == 0 and (time.time() - last_access_time) > IDLE_TIMEOUT:
            with ai_lock: 
                boxes_to_draw = []
                current_stats["status"] = "Idling"
            time.sleep(1)
            continue
            
        with ai_lock: 
            if new_frame_available and latest_frame_for_ai is not None:
                frame = latest_frame_for_ai.copy()
                new_frame_available = False
            else:
                frame = None
            
        if frame is None:
            time.sleep(0.02)
            continue
            
        try:
            results = model.track(frame, persist=True, conf=0.25, imgsz=AI_RESOLUTION, tracker="bytetrack.yaml", verbose=False)
            new_boxes = []
            current_ids = set()
            counts = {}
            
            if len(results[0].boxes) > 0:
                xyxy = results[0].boxes.xyxy.cpu().numpy().astype(int)
                cls_data = results[0].boxes.cls.cpu().numpy().astype(int)
                
                if results[0].boxes.id is not None:
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                else:
                    track_ids = [None] * len(xyxy) 

                for box, obj_id, cls in zip(xyxy, track_ids, cls_data):
                    lbl = CLASS_NAMES.get(cls, "Object")
                    
                    if obj_id is not None:
                        label_str = f"{lbl} #{obj_id}"
                        current_ids.add(obj_id) 
                    else:
                        label_str = f"{lbl} (Tracking...)"
                        
                    new_boxes.append((*box, label_str))
                    counts[lbl] = counts.get(lbl, 0) + 1
                    
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


def engine_loop():
    global output_frame, latest_frame_for_ai, new_frame_available
    print("⚙️ [ENGINE] Main engine loop starting.")
    cam = OnDemandCamera("rtsp://127.0.0.1:8554/video_feed")
    threading.Thread(target=ai_worker, daemon=True).start()
    
    while True:
        is_idle = active_viewers == 0 and (time.time() - last_access_time) > IDLE_TIMEOUT
        
        if is_idle:
            if cam.is_running:
                cam.stop()
            with lock: 
                output_frame = STANDBY_FRAME
            with ai_lock:
                latest_frame_for_ai = None 
            time.sleep(1)
            continue
            
        if not cam.is_running:
            cam.start()
            
        success, frame = cam.read()
        
        if not success:
            error_img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8)
            cv2.putText(error_img, "Stream Dropped. Reconnecting...", (100, FRAME_HEIGHT//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            _, err_encoded = cv2.imencode('.jpg', error_img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            with lock:
                output_frame = bytearray(err_encoded)
            time.sleep(0.5)
            continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # --- Night Vision Enhancement (CLAHE) ---
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l_channel)
        limg = cv2.merge((cl,a,b))
        frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        # ----------------------------------------
        
        with ai_lock:
            latest_frame_for_ai = frame.copy()
            new_frame_available = True
            cur_boxes = boxes_to_draw.copy()
            
        for (x1, y1, x2, y2, label) in cur_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        with lock:
            _, en = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            output_frame = bytearray(en)
            
        time.sleep(0.01)

# --- UPDATED VIDEO FEED ROUTINE ---
@app.route("/video_feed")
def video_feed():
    global active_viewers, last_access_time
    
    def generate():
        global active_viewers, last_access_time
        active_viewers += 1
        print(f"🔌 Client connected. Total active viewers: {active_viewers}")
        
        try:
            while True:
                last_access_time = time.time()
                with lock: 
                    frame = output_frame
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1.0 / FPS_LIMIT)
        except (GeneratorExit, Exception) as e:
            pass
        finally:
            active_viewers = max(0, active_viewers - 1)
            print(f"🔌 Client disconnected. Total active viewers: {active_viewers}")
            last_access_time = time.time()

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    global last_access_time
    return jsonify(current_stats)

if __name__ == "__main__":
    threading.Thread(target=engine_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)