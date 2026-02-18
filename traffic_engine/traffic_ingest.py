import time
import requests
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- CONFIG ---
# We talk to localhost because 'network_mode: host' shares the network stack
API_URL = "http://localhost:5000/api/stats"

# InfluxDB Settings (Loaded from your Docker Secrets)
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086") 
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "primary")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "traffic")

print("⏳ [INGEST] Waiting 15s for Traffic Engine to boot...")
time.sleep(15) 

# Connect to Database
client = None
write_api = None

try:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print(f"✅ [INGEST] Connected to InfluxDB: {INFLUX_URL}")
except Exception as e:
    print(f"❌ [INGEST] Database Connection Failed: {e}")

last_total_sent = 0

while True:
    try:
        # 1. Get Live Data
        response = requests.get(API_URL, timeout=2)
        if response.status_code == 200:
            data = response.json()
            
            # 2. Filter data (We only want counts like 'CAR': 1)
            live_counts = {k: v for k, v in data.items() 
                          if isinstance(v, (int, float)) and k not in ['total_all_time']}
            
            # 3. Write Live Counts to DB
            if live_counts and write_api:
                point = Point("traffic_live")
                has_data = False
                for label, count in live_counts.items():
                    point = point.field(label, count)
                    if count > 0: has_data = True
                
                if has_data:
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    print(f"📝 [SAVED] {live_counts}")

            # 4. Write "Total All Time"
            total = data.get('total_all_time', 0)
            if total > 0 and total != last_total_sent and write_api:
                 p = Point("traffic_stats").field("total_detections_all_time", total)
                 write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                 last_total_sent = total

    except Exception as e:
        print(f"⚠️ [INGEST ERROR] {e}")
        
    time.sleep(1.0)