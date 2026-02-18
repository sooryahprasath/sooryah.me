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

# Camera Config from Environment Variables
user = os.getenv('CAMERA_USER')
pwd = os.getenv('CAMERA_PASS')
ip = os.getenv('CAMERA_IP')
RTSP_URL = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=4&subtype=0"

# Settings
FRAME_WIDTH = 640  # Resize to 640p to save CPU
FRAME_HEIGHT = 360

# Global State
output_frame = None
current_count = 0
lock = threading.Lock()

def process_stream():
    global output_frame, current_count

    while True:
        cap = cv2.VideoCapture(RTSP_URL)

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # 1. Resize Frame (Critical for CPU performance)
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # 2. Run AI Inference
            # Classes: 2=car, 3=motorcycle, 5=bus, 7=truck
            results = model(frame, classes=[2, 3, 5, 7], verbose=False)

            count = 0
            for r in results:
                boxes = r.boxes
                count = len(boxes)
                # Draw boxes on the frame
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 3. Update State
            with lock:
                current_count = count
                # Compress to JPEG for the web stream
                (flag, encodedImage) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if flag:
                    output_frame = bytearray(encodedImage)

            # Cap at ~15 FPS to prevent CPU overheating
            time.sleep(0.06)

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
        time.sleep(0.06)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify({"cars": current_count})

if __name__ == "__main__":
    # Start the camera thread in the background
    t = threading.Thread(target=process_stream)
    t.daemon = True
    t.start()

    # Start the Web Server
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)