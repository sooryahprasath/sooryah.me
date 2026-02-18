FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# REMOVE the explicit COPY static line that is causing the error
# The 'COPY . .' below will handle everything if files exist, 
# but if you moved everything to traffic_engine, this container might be empty.
COPY . .

# Run on Port 8090
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]