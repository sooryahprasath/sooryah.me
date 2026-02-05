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

# 1. LIVE PROXY
@app.get("/api/live")
async def get_live_radar():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://{RADAR_IP}:30053/ajax/aircraft", timeout=2.0)
            return resp.json()
        except:
            return {"aircraft": {}}

# 2. HISTORY API (Traffic Volume)
@app.get("/api/history")
def get_history():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "airspace_metrics")
          |> filter(fn: (r) => r["_field"] == "aircraft_count")
          |> aggregateWindow(every: 30m, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        labels = []
        data = []
        for table in result:
            for record in table.records:
                labels.append(record.get_time().strftime("%H:%M"))
                data.append(round(record.get_value(), 1))
        return {"labels": labels, "data": data}
    except Exception as e:
        print(f"Influx Error: {e}")
        return {"labels": [], "data": []}

# 3. ALTITUDE DISTRIBUTION API
@app.get("/api/altitude")
def get_altitude():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Query last 1 hour of snapshots to get current distribution
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude")
          |> keep(columns: ["_value"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        
        altitudes = []
        for table in result:
            for record in table.records:
                altitudes.append(record.get_value())
        
        # Create buckets
        buckets = {"0-5k": 0, "5k-15k": 0, "15k-25k": 0, "25k-35k": 0, "35k+": 0}
        for alt in altitudes:
            if alt < 5000: buckets["0-5k"] += 1
            elif alt < 15000: buckets["5k-15k"] += 1
            elif alt < 25000: buckets["15k-25k"] += 1
            elif alt < 35000: buckets["25k-35k"] += 1
            else: buckets["35k+"] += 1
            
        return {"labels": list(buckets.keys()), "data": list(buckets.values())}
    except Exception:
        return {"labels": [], "data": []}

# 4. OPERATOR LEADERBOARD API
@app.get("/api/operators")
def get_operators():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["tag"] == "airline")
        '''
        # Note: Optimization - simpler to just query raw if volume low, or use flux 'count'
        # For simplicity, let's query raw snapshots from last 30m and aggregate in Python
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30m)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude")
          |> keep(columns: ["airline"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        
        airlines = []
        for table in result:
            for record in table.records:
                airlines.append(record.values.get("airline", "Unknown"))
        
        # Top 5
        counts = Counter(airlines).most_common(5)
        return {"labels": [x[0] for x in counts], "data": [x[1] for x in counts]}
    except Exception:
        return {"labels": [], "data": []}