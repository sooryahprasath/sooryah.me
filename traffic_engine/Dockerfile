FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 1. Install CPU-only PyTorch (Saves ~5GB of download)
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install Dependencies (ADDED influxdb-client here)
RUN pip install flask opencv-python-headless ultralytics influxdb-client

# 3. Copy ALL application files (FIXED: Copies traffic_ingest.py too)
COPY . .

# Default command (can be overridden by docker-compose)
CMD ["python", "traffic.py"]