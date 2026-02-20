FROM python:3.9-slim
WORKDIR /app

# Added ffmpeg to handle the RTSP stream decoding
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install flask flask-cors opencv-python-headless ultralytics influxdb-client requests

COPY . .

EXPOSE 5000
CMD ["python", "traffic.py"]