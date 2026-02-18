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
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

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
        res1 = query_api.query(org=INFLUX_ORG, query=q1)
        res2 = query_api.query(org=INFLUX_ORG, query=q2)
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
    try:
        client = get_influx_client()
        query_api = client.query_api()
        config = {"5m": ("-5m", "10s"), "15m": ("-15m", "30s"), "3h": ("-3h", "5m"), "24h": ("-24h", "30m"), "7d": ("-7d", "3h"), "14d": ("-14d", "6h"), "30d": ("-30d", "12h")}
        start, window = config.get(range_type, ("-24h", "30m"))
        query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: {start}) |> filter(fn: (r) => r["_measurement"] == "airspace_metrics") |> filter(fn: (r) => r["_field"] == "aircraft_count") |> aggregateWindow(every: {window}, fn: mean, createEmpty: false) |> yield(name: "mean")'
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels, data, ist_delta = [], [], timedelta(hours=5, minutes=30)
        for t in result:
            for r in t.records:
                local_time = r.get_time() + ist_delta
                fmt = "%d/%m %Hh" if range_type in ["7d", "14d", "30d"] else "%H:%M"
                labels.append(local_time.strftime(fmt))
                data.append(round(r.get_value(), 1))
        return {"labels": labels, "data": data}
    except: return {"labels": [], "data": []}

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
    """MJPEG Proxy Generator: Pipes the infinite stream from Port 5000 to Port 8090"""
    async def stream_generator():
        async with httpx.AsyncClient() as client:
            try:
                # timeout=None is critical for infinite streams
                async with client.stream("GET", "http://localhost:5000/video_feed", timeout=None) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk
            except Exception as e:
                print(f"Proxy Stream Error: {e}")

    return StreamingResponse(
        stream_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )