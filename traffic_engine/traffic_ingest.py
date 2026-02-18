import time
import requests
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Local connection works because of network_mode: host
API_URL = "http://localhost:5000/api/stats"

# Load secrets from Environment
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "traffic")

print("⏳ [INGEST] Initializing Ingest Service...")

def run_ingest():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    last_total = 0
    
    while True:
        try:
            # 1. Get Live Data
            resp = requests.get(API_URL, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                
                # 2. Extract Detections
                # JSON looks like: {"CAR":2, "PERSON":1, "total_all_time": 2 ...}
                live_counts = {k: v for k, v in data.items() 
                              if isinstance(v, (int, float)) and k not in ['total_all_time']}
                
                # 3. Write Live Snapshot
                if live_counts:
                    p = Point("traffic_live")
                    for label, count in live_counts.items():
                        p = p.field(label, count)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)

                # 4. Write Total for All-Time Counter
                total = data.get('total_all_time', 0)
                if total > last_total:
                    p_total = Point("traffic_stats").field("total_count", total)
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p_total)
                    last_total = total
                    print(f"📊 [SAVED] Total Detections Updated: {total}")

        except Exception as e:
            print(f"⚠️ [INGEST ERROR] {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    time.sleep(10) # Wait for engine to stabilize
    run_ingest()