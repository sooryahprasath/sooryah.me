import time
import requests
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Using localhost because of network_mode: host
API_URL = "http://localhost:5000/api/stats"

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "traffic")

print("🚀 [INGEST] Starting Traffic Ingest Service...")

def run():
    # Wait for the main engine to be up
    time.sleep(10)
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        print(f"✅ [INGEST] Connected to InfluxDB: {INFLUX_URL}")
    except Exception as e:
        print(f"❌ [INGEST] Connection Failed: {e}")
        return

    last_total = 0

    while True:
        try:
            r = requests.get(API_URL, timeout=2)
            if r.status_code == 200:
                data = r.json()
                
                # 1. Save Live Snapshots (for the "Active Targets" tiles)
                live_counts = {k: v for k, v in data.items() if isinstance(v, int) and k != 'total_all_time'}
                if live_counts:
                    p = Point("traffic_live")
                    for label, val in live_counts.items():
                        p = p.field(label, val)
                    write_api.write(bucket=INFLUX_BUCKET, record=p)

                # 2. Save Persistent Total (for the Top Counter)
                total = data.get('total_all_time', 0)
                if total > last_total:
                    p_total = Point("traffic_stats").field("total_detections", total)
                    write_api.write(bucket=INFLUX_BUCKET, record=p_total)
                    last_total = total
                    print(f"📊 [INGEST] Logged new total: {total}")

        except Exception as e:
            print(f"⚠️ [INGEST] Loop error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    run()