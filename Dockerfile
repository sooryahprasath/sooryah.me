FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly copy static to ensure it exists
COPY static ./static
COPY . .

# Run on Port 8090 to avoid conflict with Portainer/System
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]