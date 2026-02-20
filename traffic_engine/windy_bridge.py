import cv2
import os
import time
from flask import Flask, Response

app = Flask(__name__)

# Force FFmpeg to use TCP and set a 5-second timeout
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

def generate_frames():
    # Connect to the local MediaMTX stream
    cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
    
    while True:
        success, frame = cap.read()
        if not success:
            cap.release()
            time.sleep(2) # Wait before reconnecting
            cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
            continue
        
        # JPEG quality 30 is the sweet spot for Windy.com ingestion
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
        if ret:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# This handles both /video_feed and /video_feed/
@app.route('/video_feed/')
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Binding to 5500 directly as requested
    app.run(host='0.0.0.0', port=5500)