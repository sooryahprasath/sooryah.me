import cv2
import time
import os
import threading
from flask import Flask, Response, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIGURATION ---
FRAME_WIDTH = 854
FRAME_HEIGHT = 480
CONFIDENCE_THRESHOLD = 0.45
# Only run AI every X frames (higher = less CPU, lower = smoother tracking)
AI_INTERVAL = 3 

# Mapping COCO Class IDs to Human Readable Names
CLASS_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow"
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# --- GLOBAL STATE ---
output_frame = None
current_stats = {name: 0 for name in CLASS_NAMES.values()}
lock = threading.Lock()

# --- 1. THREADED CAMERA CLASS (The Speed Booster) ---
class ThreadedCamera:
    def __init__(self, src):
        self.capture = cv2.VideoCapture(src)
        # Set small buffer to prevent lag
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.started = False
        self.status = False
        self.frame = None

    def start(self):
        if self.started: return None
        self.started = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
            time.sleep(0.01) # Small sleep to prevent locking CPU

    def get_frame(self):
        return self.frame

# --- MAIN PROCESSING ENGINE ---
def start_engine():
    global output_frame, current_stats
    
    print("🚀 Loading AI Model...")
    # Load model and export to OpenVINO for 2x CPU Speed
    # usage: 'yolov8n.pt' -> auto-export -> 'yolov8n_openvino_model/'
    model = YOLO("yolov8n.pt")
    
    # Check if OpenVINO export exists, if not, create it
    if not os.path.exists("yolov8n_openvino_model"):
        print("⚙️ Optimizing model for Intel CPU (OpenVINO)... This takes 1 min...")
        model.export(format="openvino")
        print("✅ Optimization Complete!")
    
    # Load the optimized model
    ov_model = YOLO("yolov8n_openvino_model/", task="detect")

    # Camera Setup
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    print(f"📡 Connecting to Camera stream...")
    cam = ThreadedCamera(rtsp_url).start()
    
    # Wait for first frame
    time.sleep(2)
    
    frame_counter = 0
    last_boxes = [] # To draw on skipped frames

    while True:
        frame = cam.get_frame()
        
        if frame is None:
            # If camera disconnects, wait and retry
            time.sleep(1)
            continue

        # Resize for performance
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # --- AI INFERENCE (Skipped frames for speed) ---
        if frame_counter % AI_INTERVAL == 0:
            # Run Inference on the optimized model
            results = ov_model(frame, classes=TARGET_CLASSES, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            # Reset stats
            new_stats = {name: 0 for name in CLASS_NAMES.values()}
            last_boxes = []

            for r in results:
                for box in r.boxes:
                    # Get coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    
                    # Store box for drawing
                    label = CLASS_NAMES.get(cls_id, "Unknown")
                    last_boxes.append((x1, y1, x2, y2, label))
                    
                    # Update Count
                    if label in new_stats:
                        new_stats[label] += 1
            
            # Update global stats safely
            with lock:
                current_stats = new_stats

        # --- DRAWING (Happens every frame for smoothness) ---
        for (x1, y1, x2, y2, label) in last_boxes:
            # Draw Green Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Draw Label Background
            cv2.rectangle(frame, (x1, y1-20), (x1+100, y1), (0, 255, 0), -1)
            # Draw Label Text
            cv2.putText(frame, label, (x1+5, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

        frame_counter += 1

        # --- STREAM ENCODING ---
        with lock:
            # Quality 80 is the sweet spot for Stream vs CPU
            (_, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            output_frame = bytearray(encodedImage)
        
        # Cap logic loop at ~30 FPS to prevent CPU waste
        time.sleep(0.03)

# --- FLASK SERVER ---
def generate():
    while True:
        with lock:
            if output_frame is None:
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        time.sleep(0.04) # 25 FPS Stream Limit

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify(current_stats)

if __name__ == "__main__":
    # Start engine in background
    t = threading.Thread(target=start_engine)
    t.daemon = True
    t.start()
    
    # Run server
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)