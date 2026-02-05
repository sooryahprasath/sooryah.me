from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from influxdb_client import InfluxDBClient
import httpx
import os
from collections import Counter
from datetime import datetime, timedelta

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
        q1 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot" and r._field=="speed") |> group(columns:["icao_hex"]) |> count() |> group() |> count()'
        q2 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot" and (r._field=="speed" or r._field=="altitude")) |> max()'
        
        res1 = query_api.query(org=INFLUX_ORG, query=q1)
        res2 = query_api.query(org=INFLUX_ORG, query=q2)
        
        unique = res1[0].records[0].get_value() if res1 and res1[0].records else 0
        max_s, max_a = 0, 0
        for t in res2:
            for r in t.records:
                if r.get_field() == "speed": max_s = r.get_value()
                if r.get_field() == "altitude": max_a = r.get_value()

        return {"unique": unique, "speed": f"{max_s} kts", "alt": f"{max_a} ft"}
    except:
        return {"unique": 0, "speed": "0", "alt": "0"}

# --- 3. TRAFFIC HISTORY (IST TIMEZONE & BUCKETS) ---
@app.get("/api/history")
def get_history(offset: int = 0, bucket: str = "30m"):
    try:
        client = get_influx_client()
        query_api = client.query_api()
        
        start = f"-{24 * (offset + 1)}h"
        stop = f"-{24 * offset}h"
        if offset == 0: stop = "now()"
        
        # Valid buckets for the filter buttons
        if bucket not in ["5m", "15m", "30m", "1h", "3h"]: bucket = "30m"

        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {start}, stop: {stop})
          |> filter(fn: (r) => r["_measurement"] == "airspace_metrics")
          |> filter(fn: (r) => r["_field"] == "aircraft_count")
          |> aggregateWindow(every: {bucket}, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data = [], []
        
        # IST Offset (UTC + 5:30)
        ist_delta = timedelta(hours=5, minutes=30)

        for t in result:
            for r in t.records:
                # Convert to IST
                local_time = r.get_time() + ist_delta
                labels.append(local_time.strftime("%H:%M"))
                data.append(round(r.get_value(), 1))
        return {"labels": labels, "data": data}
    except Exception as e:
        print(f"History Error: {e}")
        return {"labels": [], "data": []}

# --- 4. PHYSICS SCATTER ---
@app.get("/api/scatter")
def get_scatter():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Ensure we get data even if sparse
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude" or r["_field"] == "temp_c")
          |> pivot(rowKey:["_time", "icao_hex"], columnKey: ["_field"], valueColumn: "_value")
          |> filter(fn: (r) => exists r.altitude and exists r.temp_c)
          |> sample(n: 200)
          |> keep(columns: ["altitude", "temp_c"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        data = [{"x": r["temp_c"], "y": r["altitude"]} for t in result for r in t.records]
        return data
    except:
        return []

# --- 5. DAILY BAR CHART ---
@app.get("/api/daily")
def get_daily():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -7d)
          |> filter(fn: (r) => r["_measurement"] == "airspace_metrics")
          |> filter(fn: (r) => r["_field"] == "aircraft_count")
          |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data = [], []
        # IST Offset for days
        ist_delta = timedelta(hours=5, minutes=30)
        
        for t in result:
            for r in t.records:
                local_time = r.get_time() + ist_delta
                labels.append(local_time.strftime("%a %d"))
                data.append(r.get_value())
        return {"labels": labels, "data": data}
    except:
        return {"labels": [], "data": []}

# --- 6. ALTITUDE & POLAR ---
@app.get("/api/altitude")
def get_altitude():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Scan 30 days
        query = f'''from(bucket: "{INFLUX_BUCKET}") |> range(start: -30d) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot" and r["_field"] == "altitude") |> sample(n: 1000)'''
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
    except: return {"labels": [], "data": []}

@app.get("/api/direction")
def get_direction():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'''from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot" and r["_field"] == "bearing") |> sample(n: 200)'''
        result = query_api.query(org=INFLUX_ORG, query=query)
        counts = [0]*8
        for t in result:
            for r in t.records:
                b = r.get_value()
                if b is not None: counts[int((b + 22.5) // 45) % 8] += 1
        return {"data": counts}
    except: return {"data": [0]*8}