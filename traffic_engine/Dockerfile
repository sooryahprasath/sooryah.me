FROM python:3.9-slim

WORKDIR /app

# Install system libraries required for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install flask opencv-python-headless ultralytics

# Copy our script
COPY traffic.py .

CMD ["python", "traffic.py"]