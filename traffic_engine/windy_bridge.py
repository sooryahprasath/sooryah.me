import cv2
import os
import time
from flask import Flask, Response

app = Flask(__name__)

# FFmpeg settings for stable RTSP over TCP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

def generate_frames():
    # 🔥 MOVE Capture inside the generator so it only starts when someone connects
    cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
    
    try:
        while True:
            success, frame = cap.read()
            if not success:
                # If camera fails, wait and retry
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
                continue
            
            # Sweet spot for low-bandwidth Windy ingestion
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # 🛑 THE FIX: Force the CPU to sleep for 1 second between frames.
            # Windy needs snapshots, not 60FPS. This will drop CPU from 50% to ~2%.
            time.sleep(1.0) 

    finally:
        # 🧹 Crucial: Release the camera if the client (Windy) disconnects
        print("Client disconnected, releasing resources.")
        cap.release()

@app.route('/video_feed/')
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5500, threaded=True)