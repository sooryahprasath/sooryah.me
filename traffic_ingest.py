import time
import os
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

URL = os.getenv("INFLUX_URL")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

def ingest_traffic():
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        try:
            # Get current tracking stats from Frigate
            r = requests.get("http://localhost:5000/api/stats", timeout=5)
            data = r.json()
            
            # Extract detection FPS as a proxy for 'active tracking'
            cars = data.get('intersection', {}).get('detection_fps', 0)
            
            point = Point("traffic_metrics") \
                .field("car_count", int(cars))
            
            write_api.write(bucket=BUCKET, org=ORG, record=point)
        except Exception as e:
            print(f"Traffic Error: {e}")
        time.sleep(10) # Log every 10 seconds

if __name__ == "__main__":
    ingest_traffic()