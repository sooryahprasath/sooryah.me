FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 1. Install CPU-only PyTorch
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install All Dependencies (including influxdb-client)
RUN pip install flask opencv-python-headless ultralytics influxdb-client requests

# 3. Copy EVERYTHING in the folder (Fixes the missing file error)
COPY . .

# Default command
CMD ["python", "traffic.py"]