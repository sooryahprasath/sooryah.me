FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install AI and DB libraries
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install flask opencv-python-headless ultralytics influxdb-client requests

# COPY ALL FILES (This ensures traffic_ingest.py is included)
COPY . .

# Default to engine, but compose will override for the ingest service
CMD ["python", "traffic.py"]