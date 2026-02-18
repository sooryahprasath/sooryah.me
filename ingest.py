import time
import os
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# CONFIG - Environment variables passed via docker-compose
URL = os.getenv("INFLUX_URL")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")
RADAR_SOURCE = f"http://{os.getenv('RADAR_IP')}:30053/ajax/aircraft"

def get_airline_code(callsign):
    """Extracts the 3-letter ICAO airline code from a callsign."""
    if not callsign or len(callsign) < 3: return "Unknown"
    return callsign[:3]

def ingest():
    print(f"--- Starting Mission Control Ingest (v3) ---", flush=True)
    
    try:
        # Initialize InfluxDB Client
        client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        print(f"✅ Connected to InfluxDB at {URL}", flush=True)
    except Exception as e:
        print(f"❌ InfluxDB Connection Failed: {e}", flush=True)
        return

    while True:
        try:
            # Fetch data from the local radar source (RTL-SDR/Dump1090)
            r = requests.get(RADAR_SOURCE, timeout=5)
            if r.status_code != 200:
                print(f"⚠️ Radar Error: {r.status_code}", flush=True)
                time.sleep(10)
                continue
                
            data = r.json()
            aircraft = data.get('aircraft', {})
            
            # --- 1. GLOBAL METRICS (Time Series for Dashboard KPI) ---
            count = len(aircraft)
            # Filter valid distances to find maximum range
            distances = [float(p.get('polar_distance', 0)) for p in aircraft.values() if p.get('polar_distance')]
            max_dist = max(distances) if distances else 0.0
            
            p_global = Point("airspace_metrics") \
                .field("aircraft_count", int(count)) \
                .field("max_range_nm", float(max_dist))
            
            write_api.write(bucket=BUCKET, org=ORG, record=p_global)

            # --- 2. DETAILED SNAPSHOTS (For Scatter/Polar/KPIs) ---
            batch = []
            for hex_code, p in aircraft.items():
                # Filter: Ignore if altitude or position is missing for reliable tracking
                if 'altitude' not in p or p['altitude'] is None: continue
                if 'lat' not in p or 'lon' not in p: continue
                
                # Filter: Cap Speed at 650kts (Mach 0.98) to remove GPS/SDR glitches
                speed = int(p.get('speed', 0))
                if speed > 650: continue

                # Capture Physics and Position Data
                point = Point("aircraft_snapshot") \
                    .tag("icao_hex", hex_code) \
                    .tag("airline", get_airline_code(p.get('callsign', ''))) \
                    .tag("type", p.get('type', 'Unknown')) \
                    .field("altitude", int(p['altitude'])) \
                    .field("speed", speed) \
                    .field("distance", float(p.get('polar_distance', 0))) \
                    .field("bearing", float(p.get('polar_bearing', 0))) \
                    .field("temp_c", float(p.get('oat', 0)))  # Outside Air Temp
                
                batch.append(point)
            
            # Write batch of snapshots to InfluxDB
            if batch:
                write_api.write(bucket=BUCKET, org=ORG, record=batch)

            print(f"📊 Logged: {count} planes | {len(batch)} valid snapshots", flush=True)

        except Exception as e:
            print(f"⚠️ Ingest Error: {e}", flush=True)
        
        # 10-second interval to balance detail with InfluxDB storage
        time.sleep(10)

if __name__ == "__main__":
    ingest()