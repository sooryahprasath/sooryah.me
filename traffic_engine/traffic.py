import cv2
import time
import os
import threading
import datetime
from flask import Flask, Response, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- MIDDLE GROUND CONFIGURATION ---
FRAME_WIDTH = 854
FRAME_HEIGHT = 480
FPS_LIMIT = 15          # Locks video to 15 FPS (Quiet CPU)
AI_INTERVAL_SEC = 0.5   # Run AI only once every 0.5 seconds (Very Stable)

CLASS_NAMES = {
    0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK",
    14: "BIRD", 15: "CAT", 16: "DOG", 17: "HORSE", 18: "SHEEP", 19: "COW"
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# --- GLOBAL STATE ---
output_frame = None
current_stats = {}
lock = threading.Lock()

# --- ROBUST CAMERA CLASS ---
class RobustCamera:
    def __init__(self, src):
        self.src = src
        self.cap = None
        self.frame = None
        self.running = True
        self.last_frame_time = time.time()
        self.lock = threading.Lock()
        
        # Start the background thread
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            # 1. Connect if not connected
            if self.cap is None or not self.cap.isOpened():
                print(f"🔄 Connecting to camera...")
                self.cap = cv2.VideoCapture(self.src)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Reduce latency
                time.sleep(1) # Give it a moment to stabilize
                if not self.cap.isOpened():
                    print("❌ Connection failed. Retrying in 5s...")
                    time.sleep(5)
                    continue
            
            # 2. Read Frame
            success, frame = self.cap.read()
            
            # 3. Handle Success/Failure
            if success:
                with self.lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                
                # FPS LIMITER: Sleep to match target FPS
                time.sleep(1.0 / FPS_LIMIT)
            else:
                print("⚠️ Stream packet dropped/empty.")
                time.sleep(0.5)
                # If no frames for 5 seconds, force reconnect
                if time.time() - self.last_frame_time > 5:
                    print("❌ Watchdog: Camera frozen. Restarting...")
                    self.cap.release()
                    self.cap = None

    def get_frame(self):
        with self.lock:
            return self.frame

# --- MAIN ENGINE ---
def start_engine():
    global output_frame, current_stats
    
    print("🚀 Loading AI Model (Standard Mode)...")
    # Using standard model is safer for stability than custom OpenVINO export sometimes
    model = YOLO("yolov8n.pt") 
    
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cam = RobustCamera(rtsp_url)
    
    # State for visuals
    last_ai_time = 0
    last_boxes = [] # Persist boxes between AI runs
    
    print("✅ Engine Started. Waiting for frames...")

    while True:
        frame = cam.get_frame()
        
        if frame is None:
            time.sleep(0.1)
            continue

        # Resize first (Saves CPU on drawing/encoding)
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # --- AI INFERENCE (Time Controlled) ---
        now = time.time()
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            
            # Run Inference in a separate try/except block so it never crashes video
            try:
                results = model(frame, classes=TARGET_CLASSES, verbose=False)
                
                temp_stats = {}
                temp_boxes = []
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls_id = int(box.cls[0])
                        label = CLASS_NAMES.get(cls_id, "Unknown")
                        
                        temp_boxes.append((x1, y1, x2, y2, label))
                        
                        if label in temp_stats: temp_stats[label] += 1
                        else: temp_stats[label] = 1
                
                # Update global state
                last_boxes = temp_boxes
                with lock:
                    # Add timestamp for the "Chat Log" feature
                    if temp_stats:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        details = ", ".join([f"{k}: {v}" for k,v in temp_stats.items()])
                        log_msg = f"[{timestamp}] DETECTED: {details}"
                        temp_stats['log'] = log_msg
                    
                    current_stats = temp_stats
                    
            except Exception as e:
                print(f"⚠️ AI Error: {e}")

        # --- DRAWING (Draws every frame for smoothness) ---
        for (x1, y1, x2, y2, label) in last_boxes:
            # Draw Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Draw Label
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # --- ENCODING ---
        with lock:
            # Quality 60 is perfectly fine for monitoring and saves bandwidth/CPU
            (_, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            output_frame = bytearray(encodedImage)
        
        # Main loop sleep (Just a tiny bit to prevent CPU spinning)
        time.sleep(0.01)

def generate():
    while True:
        with lock:
            if output_frame is None:
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        # Stream at same rate as Capture (15 FPS)
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
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)