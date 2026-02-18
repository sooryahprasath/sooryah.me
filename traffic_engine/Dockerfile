FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 1. Install CPU-only PyTorch (Saves ~5GB of download)
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install Ultralytics (Will skip GPU libs since torch is already installed)
RUN pip install flask opencv-python-headless ultralytics

# Copy application
COPY traffic.py .

CMD ["python", "traffic.py"]