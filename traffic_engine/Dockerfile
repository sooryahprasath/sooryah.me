FROM python:3.9-slim
WORKDIR /app

# Added ffmpeg to handle the RTSP stream decoding
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*

# Install PyTorch
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install all required dependencies (Added openvino here!)
RUN pip install flask flask-cors opencv-python-headless ultralytics influxdb-client requests openvino

# 1. COPY the application files into the container FIRST
COPY . .

# 2. NOW compile the model (because uvh_26_blr_8k.pt is finally inside /app)
RUN yolo export model=uvh_26_blr_8k.pt format=openvino

EXPOSE 5000
CMD ["python", "traffic.py"]