import cv2
from flask import Flask, Response

app = Flask(__name__)

def generate_frames():
    # Pull from the internal MediaMTX RTSP port
    cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/video_feed")
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # High compression (quality 30) makes it load instantly on Windy
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # We use 8083 because that's what your Cloudflare is likely expecting
    app.run(host='0.0.0.0', port=8083)