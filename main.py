from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from influxdb_client import InfluxDBClient
import httpx
import os
from collections import Counter

app = FastAPI()

# CONFIG
RADAR_IP = os.getenv("RADAR_IP")
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

def get_influx_client():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- 1. LIVE PROXY ---
@app.get("/api/live")
async def get_live_radar():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://{RADAR_IP}:30053/ajax/aircraft", timeout=2.0)
            return resp.json()
        except:
            return {"aircraft": {}}

# --- 2. KPI ENDPOINT ---
@app.get("/api/kpi")
def get_kpi():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        
        # Unique Planes (Rolling 24h)
        q1 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot") |> filter(fn:(r)=>r._field=="speed") |> group(columns:["icao_hex"]) |> count() |> group() |> count()'
        # Max Stats (Today)
        q2 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot" and (r._field=="speed" or r._field=="altitude")) |> max()'
        
        res1 = query_api.query(org=INFLUX_ORG, query=q1)
        res2 = query_api.query(org=INFLUX_ORG, query=q2)
        
        unique = res1[0].records[0].get_value() if res1 and res1[0].records else 0
        max_s, max_a = 0, 0
        for t in res2:
            for r in t.records:
                if r.get_field() == "speed": max_s = r.get_value()
                if r.get_field() == "altitude": max_a = r.get_value()

        return {"unique_planes_24h": unique, "max_speed_24h": f"{max_s} kts", "max_alt_24h": f"{max_a} ft"}
    except:
        return {"unique_planes_24h": 0, "max_speed_24h": "0", "max_alt_24h": "0"}

# --- 3. DAILY HISTORY (7 DAYS) ---
@app.get("/api/daily")
def get_daily_flights():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Get Max Simultaneous Flights per day as a proxy for busyness
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -7d)
          |> filter(fn: (r) => r["_measurement"] == "airspace_metrics")
          |> filter(fn: (r) => r["_field"] == "aircraft_count")
          |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
          |> yield(name: "max")
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data = [], []
        for t in result:
            for r in t.records:
                labels.append(r.get_time().strftime("%a %d")) # e.g. "Mon 05"
                data.append(r.get_value())
        return {"labels": labels, "data": data}
    except:
        return {"labels": [], "data": []}

# --- 4. TRAFFIC VOLUME (SLICEABLE) ---
@app.get("/api/history")
def get_history(offset: int = 0):
    # offset=0 is Today, offset=1 is Yesterday...
    try:
        client = get_influx_client()
        query_api = client.query_api()
        
        start = f"-{24 * (offset + 1)}h"
        stop = f"-{24 * offset}h"
        if offset == 0: stop = "now()"
        
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {start}, stop: {stop})
          |> filter(fn: (r) => r["_measurement"] == "airspace_metrics")
          |> filter(fn: (r) => r["_field"] == "aircraft_count")
          |> aggregateWindow(every: 30m, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data = [], []
        for t in result:
            for r in t.records:
                labels.append(r.get_time().strftime("%H:%M"))
                data.append(round(r.get_value(), 1))
        return {"labels": labels, "data": data}
    except:
        return {"labels": [], "data": []}

# --- 5. PHYSICS SCATTER (Temp vs Alt) ---
@app.get("/api/scatter")
def get_scatter():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Sampled scatter data
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude" or r["_field"] == "temp_c")
          |> pivot(rowKey:["_time", "icao_hex"], columnKey: ["_field"], valueColumn: "_value")
          |> filter(fn: (r) => exists r.altitude and exists r.temp_c)
          |> sample(n: 50) 
          |> keep(columns: ["altitude", "temp_c"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        data = [{"x": r["temp_c"], "y": r["altitude"]} for t in result for r in t.records]
        return data
    except:
        return []

# --- 6. DIRECTION (POLAR) ---
@app.get("/api/direction")
def get_direction():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Count planes coming from each sector
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "bearing")
          |> sample(n: 200)
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        counts = [0]*8 # N, NE, E, SE, S, SW, W, NW
        for t in result:
            for r in t.records:
                b = r.get_value()
                if b is not None:
                    idx = int((b + 22.5) // 45) % 8
                    counts[idx] += 1
        return {"data": counts}
    except:
        return {"data": [0]*8}

# --- 7. ALTITUDE DISTRIBUTION (30 DAYS) ---
@app.get("/api/altitude")
def get_altitude():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # 30 Days of data, heavily sampled to be fast
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude")
          |> sample(n: 1000)
          |> keep(columns: ["_value"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        alts = [r.get_value() for t in result for r in t.records]
        
        buckets = {"0-5k": 0, "5k-15k": 0, "15k-25k": 0, "25k-35k": 0, "35k+": 0}
        for a in alts:
            if a < 5000: buckets["0-5k"] += 1
            elif a < 15000: buckets["5k-15k"] += 1
            elif a < 25000: buckets["15k-25k"] += 1
            elif a < 35000: buckets["25k-35k"] += 1
            else: buckets["35k+"] += 1
        return {"labels": list(buckets.keys()), "data": list(buckets.values())}
    except:
        return {"labels": [], "data": []}

# --- 8. OPERATORS ---
@app.get("/api/operators")
def get_operators():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'''from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot") |> filter(fn: (r) => r["_field"] == "altitude") |> keep(columns: ["airline"])'''
        result = query_api.query(org=INFLUX_ORG, query=query)
        airlines = [r.values.get("airline", "Unknown") for t in result for r in t.records]
        counts = Counter(airlines).most_common(5)
        return {"labels": [x[0] for x in counts], "data": [x[1] for x in counts]}
    except:
        return {"labels": [], "data": []}