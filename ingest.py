import time
import os
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# CONFIG (Loaded from Docker Compose)
URL = os.getenv("INFLUX_URL")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")
RADAR_SOURCE = f"http://{os.getenv('RADAR_IP')}:30053/ajax/aircraft"

def ingest():
    print(f"--- Starting Ingest Service for {ORG}/{BUCKET} ---")
    
    # Initialize Influx Client
    try:
        client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
    except Exception as e:
        print(f"Failed to connect to InfluxDB: {e}")
        return

    while True:
        try:
            # 1. Scrape Pi
            r = requests.get(RADAR_SOURCE, timeout=5)
            if r.status_code != 200:
                print(f"Radar unreachable: {r.status_code}")
                time.sleep(10)
                continue
                
            data = r.json()
            aircraft = data.get('aircraft', {})
            
            # 2. Extract Metrics
            count = len(aircraft)
            # Find furthest distance
            distances = [float(p.get('polar_distance', 0)) for p in aircraft.values()]
            max_dist = max(distances) if distances else 0.0
            
            # 3. Write Point
            p = Point("airspace_metrics") \
                .field("aircraft_count", int(count)) \
                .field("max_range_nm", float(max_dist))
            
            write_api.write(bucket=BUCKET, org=ORG, record=p)
            print(f"Logged: {count} planes | Range: {max_dist:.1f}nm")

        except Exception as e:
            print(f"Ingest Error: {e}")
        
        time.sleep(10) # Wait 10s

if __name__ == "__main__":
    ingest()