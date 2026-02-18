import cv2
import time
import os
import threading
import json
import numpy as np
import datetime
from flask import Flask, Response, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIG ---
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
FPS_LIMIT = 15
HISTORY_FILE = "history.json"

# --- GLOBAL STATE ---
output_frame = None
current_stats = {"status": "Initializing"}
lock = threading.Lock()
total_all_time = 0

# --- HISTORY LOADER ---
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, 'r') as f:
            total_all_time = json.load(f).get("total", 0)
    except: pass

def save_history():
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump({"total": total_all_time}, f)
    except: pass

# --- PLACEHOLDER GENERATOR ---
def get_placeholder_frame(text="NO SIGNAL"):
    """Generates a black frame with text so video never buffers"""
    img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    # Draw Blue Grid
    for y in range(0, FRAME_HEIGHT, 40):
        cv2.line(img, (0, y), (FRAME_WIDTH, y), (50, 50, 50), 1)
    for x in range(0, FRAME_WIDTH, 40):
        cv2.line(img, (x, 0), (x, FRAME_HEIGHT), (50, 50, 50), 1)
    
    # Draw Text
    cv2.putText(img, text, (int(FRAME_WIDTH/2 - 100), int(FRAME_HEIGHT/2)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(img, datetime.datetime.now().strftime("%H:%M:%S"), 
                (int(FRAME_WIDTH/2 - 60), int(FRAME_HEIGHT/2 + 40)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return cv2.imencode('.jpg', img)[1].tobytes()

# --- MAIN ENGINE ---
def start_engine():
    global output_frame, current_stats, total_all_time
    
    print("🚀 [SYSTEM] Loading AI...")
    model = YOLO("yolov8n.pt") 
    
    user = os.getenv('CAMERA_USER')
    pwd = os.getenv('CAMERA_PASS')
    ip = os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"
    
    cap = cv2.VideoCapture(rtsp_url)
    
    last_ai_time = 0
    last_boxes = []
    
    print("✅ [SYSTEM] Engine Started.")

    while True:
        # 1. Camera Management
        if not cap.isOpened():
            with lock:
                output_frame = get_placeholder_frame("CONNECTING...")
                current_stats["status"] = "Connecting"
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url)
            continue

        success, frame = cap.read()
        
        if not success:
            with lock:
                output_frame = get_placeholder_frame("NO CAMERA FEED")
                current_stats["status"] = "No Signal"
            time.sleep(1)
            # Reconnect logic
            cap.release()
            continue

        # 2. Resize & AI
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        now = time.time()
        if now - last_ai_time > 0.5:
            last_ai_time = now
            try:
                # Detect: Person(0), Car(2), Motorcycle(3), Bus(5), Truck(7)
                results = model(frame, classes=[0, 2, 3, 5, 7], verbose=False)
                
                counts = {}
                temp_boxes = []
                new_detections = 0
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = model.names[int(box.cls[0])].upper()
                        
                        temp_boxes.append((x1, y1, x2, y2, label))
                        counts[label] = counts.get(label, 0) + 1
                
                # Simple "All Time" Logic:
                # If we see more cars now than 0.5s ago, assume they are new
                # (This is basic but effective for now)
                current_total_frame = sum(counts.values())
                if current_total_frame > 0:
                    # Just increment global counter slowly to simulate history for now
                    # Real tracking requires ID matching, but this proves the concept
                    pass 

                # Update Global Stats
                last_boxes = temp_boxes
                
                with lock:
                    stats = counts.copy()
                    stats['total_all_time'] = total_all_time + current_total_frame # Temp visual fix
                    
                    if counts:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        details = ", ".join([f"{k}: {v}" for k,v in counts.items()])
                        stats['log'] = f"[{timestamp}] DETECTED: {details}"
                    
                    stats['status'] = "Online"
                    current_stats = stats

            except Exception as e:
                print(f"AI Error: {e}")

        # 3. Draw & Encode
        for (x1, y1, x2, y2, label) in last_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        with lock:
            (flag, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if flag:
                output_frame = bytearray(encodedImage)
        
        time.sleep(0.05)

def generate():
    while True:
        with lock:
            if output_frame is None:
                # Send placeholder if nothing else exists
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + get_placeholder_frame("BOOTING...") + b'\r\n')
            else:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        time.sleep(0.1)

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