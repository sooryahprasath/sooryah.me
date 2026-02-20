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

# CONFIG - MAXIMUM PERFORMANCE MODE
FRAME_WIDTH, FRAME_HEIGHT = 3072, 1728 
AI_INTERVAL_SEC = 2.0    # AI runs every 2s to keep the video stream fluid
HISTORY_FILE = "history.json"
CLASS_NAMES = {0: "PERSON", 1: "BICYCLE", 2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK"}

# GLOBAL STATE
output_frame = None
lock = threading.Lock()

# ... (HistoryManager class remains the same) ...

def start_engine():
    global output_frame, current_stats
    try:
        model = YOLO("yolov8n.pt") 
    except: return

    user, pwd, ip = os.getenv('CAMERA_USER'), os.getenv('CAMERA_PASS'), os.getenv('CAMERA_IP')
    rtsp_url = f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif"
    
    # Force TCP and High-Speed FFMPEG flags
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"
    
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    # Tell the hardware to push frames as fast as possible
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    last_ai_time = 0
    previous_raw_counts = {} 
    last_valid_counts = {}   
    temp_boxes = []

    while True:
        success, frame = cap.read()
        if not success:
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            continue

        # Process at 3K
        draw_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        now = time.time()
        
        # AI INFERENCE (Lightweight branch)
        if now - last_ai_time > AI_INTERVAL_SEC:
            last_ai_time = now
            try:
                # imgsz=320 is critical for high FPS video
                results = model(draw_frame, classes=list(CLASS_NAMES.keys()), verbose=False, imgsz=320)
                current_raw_counts = {}
                new_boxes = []
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = CLASS_NAMES.get(int(box.cls[0]), "Unknown")
                        new_boxes.append((x1, y1, x2, y2, label))
                        current_raw_counts[label] = current_raw_counts.get(label, 0) + 1
                
                temp_boxes = new_boxes
                smoothed_counts = {l: max(current_raw_counts.get(l, 0), previous_raw_counts.get(l, 0)) for l in (set(current_raw_counts) | set(previous_raw_counts))}
                new_v = sum([max(0, smoothed_counts.get(l, 0) - last_valid_counts.get(l, 0)) for l in smoothed_counts])
                if new_v > 0: history.increment(new_v)
                previous_raw_counts, last_valid_counts = current_raw_counts, smoothed_counts
                
                with lock:
                    current_stats = {"status": "3K MAX VELOCITY", "total_all_time": history.total_count, **current_raw_counts}
            except: pass

        # Graphics Overlays
        for (x1, y1, x2, y2, label) in temp_boxes:
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), (0, 255, 0), 6)
            cv2.putText(draw_frame, label, (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)

        with lock:
            # We use quality 50 to ensure the network can actually carry the 3K frames at high speed
            _, encoded = cv2.imencode(".jpg", draw_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            output_frame = bytearray(encoded)