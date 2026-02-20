import cv2
from flask import Flask, Response

app = Flask(__name__)

def generate():
    # Pull from MediaMTX internal RTSP
    cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
    while True:
        success, frame = cap.read()
        if not success: break
        # Encode as JPG for Windy
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8083)