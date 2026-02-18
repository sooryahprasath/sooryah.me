import time
import requests
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration
API_URL = "http://localhost:5000/api/stats"
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "my-bucket")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("📝 Traffic Ingest Service Started...")

# State tracking to avoid double-counting the same car 
# (e.g. if a car stays in frame for 5 seconds, we only want to count it ONCE)
last_counts = {}

while True:
    try:
        # 1. Get Live Data
        response = requests.get(API_URL, timeout=2)
        data = response.json()
        
        current_counts = {k: v for k, v in data.items() if k != 'log' and isinstance(v, int)}
        
        # 2. Logic: Only record POSITIVE changes (New arrivals)
        # Simple approach: If count increases, add the difference to DB
        timestamp = time.time_ns()
        
        for label, count in current_counts.items():
            prev = last_counts.get(label, 0)
            
            # If we see MORE cars than before, these are NEW cars
            if count > prev:
                diff = count - prev
                print(f"Detected {diff} new {label}(s). Saving to DB...")
                
                point = Point("traffic_stats") \
                    .tag("type", label) \
                    .field("count", diff) \
                    .time(timestamp)
                
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

        # Update state
        last_counts = current_counts
        
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(1.0)