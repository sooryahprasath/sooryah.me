from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from influxdb_client import InfluxDBClient
import httpx
import os
from datetime import timedelta

app = FastAPI()

# CONFIG
RADAR_IP = os.getenv("RADAR_IP")
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET") # Radar bucket

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

def get_influx_client():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- RADAR APIS ---
@app.get("/api/live")
async def get_live_radar():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://{RADAR_IP}:30053/ajax/aircraft", timeout=2.0)
            return resp.json()
        except: return {"aircraft": {}}

@app.get("/api/kpi")
def get_kpi():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        q1 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot" and r._field=="speed") |> group(columns: ["icao_hex"]) |> distinct(column: "icao_hex") |> group() |> count()'
        q2 = f'from(bucket:"{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn:(r)=>r._measurement=="aircraft_snapshot" and (r._field=="speed" or r._field=="altitude")) |> max()'
        res1, res2 = query_api.query(org=INFLUX_ORG, query=q1), query_api.query(org=INFLUX_ORG, query=q2)
        unique = res1[0].records[0].get_value() if res1 and res1[0].records else 0
        max_s, max_a = 0, 0
        for t in res2:
            for r in t.records:
                if r.get_field() == "speed": max_s = r.get_value()
                if r.get_field() == "altitude": max_a = r.get_value()
        return {"unique": unique, "speed": f"{max_s} kts", "alt": f"{max_a} ft"}
    except: return {"unique": 0, "speed": "0 kts", "alt": "0 ft"}

@app.get("/api/history")
def get_history(range_type: str = "24h"):
    """Handles timeline logic from 5 minutes to 30 days."""
    try:
        client = get_influx_client()
        query_api = client.query_api()
        config = {
            "5m": ("-5m", "10s"), "15m": ("-15m", "30s"), "3h": ("-3h", "5m"), 
            "24h": ("-24h", "30m"), "7d": ("-7d", "3h"), "14d": ("-14d", "6h"), "30d": ("-30d", "12h")
        }
        start, window = config.get(range_type, ("-24h", "30m"))
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: {start}) |> filter(fn: (r) => r["_measurement"] == "airspace_metrics" and r["_field"] == "aircraft_count") |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data, ist_delta = [], [], timedelta(hours=5, minutes=30)
        for t in result:
            for r in t.records:
                fmt = "%H:%M" if range_type in ["5m", "15m", "3h", "24h"] else "%d/%m %Hh"
                labels.append((r.get_time() + ist_delta).strftime(fmt))
                data.append(round(r.get_value(), 1))
        return {"labels": labels, "data": data}
    except: return {"labels": [], "data": []}

@app.get("/api/scatter")
def get_scatter():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot" and (r["_field"] == "altitude" or r["_field"] == "temp_c")) |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") |> filter(fn: (r) => exists r.altitude and exists r.temp_c) |> limit(n: 500)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        return [{"x": r["temp_c"], "y": r["altitude"]} for t in result for r in t.records]
    except: return []

@app.get("/api/daily")
def get_daily():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -7d) |> filter(fn: (r) => r["_measurement"] == "airspace_metrics" and r["_field"] == "aircraft_count") |> aggregateWindow(every: 1d, fn: max, createEmpty: false)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data, ist_delta = [], [], timedelta(hours=5, minutes=30)
        for t in result:
            for r in t.records:
                labels.append((r.get_time() + ist_delta).strftime("%a %d"))
                data.append(r.get_value())
        return {"labels": labels, "data": data}
    except: return {"labels": [], "data": []}

@app.get("/api/altitude")
def get_altitude():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -7d) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot" and r["_field"] == "altitude") |> sample(n: 1000)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        buckets = {"0-10k": 0, "10k-20k": 0, "20k-30k": 0, "30k-40k": 0, "40k+": 0}
        for t in result:
            for r in t.records:
                a = r.get_value()
                if a < 10000: buckets["0-10k"] += 1
                elif a < 20000: buckets["10k-20k"] += 1
                elif a < 30000: buckets["20k-30k"] += 1
                elif a < 40000: buckets["30k-40k"] += 1
                else: buckets["40k+"] += 1
        return {"labels": list(buckets.keys()), "data": list(buckets.values())}
    except: return {"labels": [], "data": []}

@app.get("/api/direction")
def get_direction():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot" and r["_field"] == "bearing") |> sample(n: 200)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        counts = [0]*8
        for t in result:
            for r in t.records:
                b = r.get_value()
                if b is not None: counts[int((b + 22.5) // 45) % 8] += 1
        return {"data": counts}
    except: return {"data": [0]*8}

# --- TRAFFIC PROXY ROUTES ---
@app.get("/api/stats")
async def proxy_stats():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:5000/api/stats", timeout=1.0)
            return resp.json()
        except: return {"status": "Offline", "total_all_time": 0}

@app.get("/video_feed")
async def proxy_video():
    """Corrected Proxy: Pipes the MJPEG stream from Port 5000 to the browser."""
    async def stream_generator():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("GET", "http://localhost:5000/video_feed", timeout=None) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk
            except Exception: pass
    return StreamingResponse(stream_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/traffic/history")
def get_traffic_history():
    """Queries vehicle data from the traffic bucket."""
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = 'from(bucket: "traffic") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "traffic_stats" and r["_field"] == "total_detections") |> aggregateWindow(every: 30m, fn: max, createEmpty: false)'
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data = [], []
        for t in result:
            for r in t.records:
                labels.append(r.get_time().strftime("%H:%M"))
                data.append(r.get_value())
        return {"labels": labels, "data": data}
    except: return {"labels": [], "data": []}