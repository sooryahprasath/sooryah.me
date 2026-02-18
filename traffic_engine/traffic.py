import cv2
import time
import os
import threading
import datetime
from flask import Flask, Response, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIGURATION ---
FRAME_WIDTH = 854
FRAME_HEIGHT = 480
CONFIDENCE_THRESHOLD = 0.45
AI_INTERVAL = 3 

CLASS_NAMES = {
    0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK",
    14: "BIRD", 15: "CAT", 16: "DOG", 17: "HORSE", 18: "SHEEP", 19: "COW"
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# --- GLOBAL STATE ---
output_frame = None
current_stats = {}
last_log_entry = "" # To avoid spamming the log
lock = threading.Lock()

# --- ROBUST CAMERA CLASS ---
class ThreadedCamera:
    def __init__(self, src):
        self.src = src
        self.capture = cv2.VideoCapture(self.src)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Low latency
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.started = False
        self.frame = None
        self.last_read_time = time.time()

    def start(self):
        if self.started: return None
        self.started = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            if self.capture.isOpened():
                (status, frame) = self.capture.read()
                if status:
                    self.frame = frame
                    self.last_read_time = time.time()
                else:
                    # Stream broken? Reconnect.
                    self.reconnect()
            else:
                self.reconnect()
            
            # Watchdog: If no new frame for 5 seconds, force reconnect
            if time.time() - self.last_read_time > 5:
                print("❌ Camera frozen. Forcing restart...")
                self.reconnect()
                
            time.sleep(0.01)

    def reconnect(self):
        print("🔄 Reconnecting to camera...")
        self.capture.release()
        time.sleep(2) # Wait before retry
        self.capture = cv2.VideoCapture(self.src)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.last_read_time = time.time() # Reset watchdog

    def get_frame(self):
        return self.frame

# --- MAIN ENGINE ---
def start_engine():
    global output_frame, current_stats, last_log_entry
    
    print("🚀 Loading AI Model...")
    model = YOLO("yolov8n.pt") 
    
    # Check for OpenVINO export (Auto-Use if exists)
    if os.path.exists("yolov8n_openvino_model"):
        print("✅ Using OpenVINO Optimized Model")
        model = YOLO("yolov8n_openvino_model/", task="detect")
    
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cam = ThreadedCamera(rtsp_url).start()
    
    frame_counter = 0
    last_boxes = []

    while True:
        frame = cam.get_frame()
        if frame is None:
            time.sleep(0.5)
            continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # --- AI INFERENCE ---
        if frame_counter % AI_INTERVAL == 0:
            results = model(frame, classes=TARGET_CLASSES, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            new_stats = {}
            last_boxes = []
            log_buffer = []

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    label = CLASS_NAMES.get(cls_id, "Unknown")
                    
                    last_boxes.append((x1, y1, x2, y2, label))
                    
                    if label in new_stats: new_stats[label] += 1
                    else: new_stats[label] = 1
            
            with lock:
                current_stats = new_stats
                # Create a log entry string if something was found
                if new_stats:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    # Format: "CAR: 2, PERSON: 1"
                    details = ", ".join([f"{k}: {v}" for k,v in new_stats.items()])
                    new_entry = f"[{timestamp}] DETECTED: {details}"
                    
                    # Only update log if it CHANGED (prevents spamming "Car: 1" 100 times)
                    if new_entry != last_log_entry:
                        current_stats['log'] = new_entry
                        last_log_entry = new_entry

        # --- DRAWING ---
        for (x1, y1, x2, y2, label) in last_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        frame_counter += 1

        with lock:
            (_, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            output_frame = bytearray(encodedImage)
        
        time.sleep(0.03)

def generate():
    while True:
        with lock:
            if output_frame is None:
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        time.sleep(0.04)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify(current_stats)

if __name__ == "__main__":
    t = threading.Thread(target=start_engine)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)