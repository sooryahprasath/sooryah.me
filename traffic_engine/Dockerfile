FROM python:3.9-slim

WORKDIR /app

# Install system libraries required for OpenCV
# FIX: Replaced 'libgl1-mesa-glx' (deprecated) with 'libgl1'
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install flask opencv-python-headless ultralytics

# Copy application
COPY traffic.py .

CMD ["python", "traffic.py"]