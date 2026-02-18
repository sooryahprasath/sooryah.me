FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# ADD flask-cors HERE
RUN pip install flask flask-cors opencv-python-headless ultralytics influxdb-client requests
COPY . .
CMD ["python", "traffic.py"]