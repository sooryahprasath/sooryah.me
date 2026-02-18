import cv2
import time
import os
import threading
from flask import Flask, Response, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# Load the nano model (optimized for CPU)
print("Loading AI Model...")
model = YOLO("yolov8n.pt") 

# Camera Config
user = os.getenv('CAMERA_USER')
pwd = os.getenv('CAMERA_PASS')
ip = os.getenv('CAMERA_IP')
RTSP_URL = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"

# Settings: 480p is a good balance of clarity vs CPU usage
FRAME_WIDTH = 854
FRAME_HEIGHT = 480

# Detection Classes (COCO Dataset IDs)
# 0:person, 1:bicycle, 2:car, 3:motorcycle, 5:bus, 7:truck, 
# 14:bird, 15:cat, 16:dog, 17:horse, 18:sheep, 19:cow
TARGET_CLASSES = [0, 1, 2, 3, 5, 7, 14, 15, 16, 17, 18, 19]

# Global State
output_frame = None
current_count = 0
lock = threading.Lock()

def process_stream():
    global output_frame, current_count
    
    # We will store the boxes from the last "detection frame" 
    # and draw them on the "skipped frames" to keep video smooth.
    last_boxes = []
    frame_counter = 0

    while True:
        cap = cv2.VideoCapture(RTSP_URL)
        # Set buffer size to 1 to reduce latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # 1. Resize Frame
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # 2. INTELLIGENT SKIPPING
            # We display every frame (smooth video), but only run AI every 4th frame (saves CPU)
            if frame_counter % 4 == 0:
                results = model(frame, classes=TARGET_CLASSES, verbose=False)
                
                # Reset boxes for this new detection
                last_boxes = [] 
                count = 0
                
                for r in results:
                    boxes = r.boxes
                    count = len(boxes)
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # Store box coordinates to draw later
                        last_boxes.append((x1, y1, x2, y2))
                
                # Update global stats
                with lock:
                    current_count = count
            
            # 3. Draw the boxes (even on skipped frames)
            for (x1, y1, x2, y2) in last_boxes:
                # Green Box with slight transparency effect
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            frame_counter += 1

            # 4. Update the Web Stream
            with lock:
                # Compression quality 70 is indistinguishable from 100 but much faster
                (flag, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if flag:
                    output_frame = bytearray(encodedImage)
            
            # Target ~20 FPS for the stream (Smooth enough, low CPU)
            time.sleep(0.05)

        cap.release()
        print("Stream disconnected. Retrying in 5s...")
        time.sleep(5)

def generate():
    while True:
        with lock:
            if output_frame is None:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        # Stream FPS control
        time.sleep(0.05)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify({"cars": current_count})

if __name__ == "__main__":
    t = threading.Thread(target=process_stream)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)