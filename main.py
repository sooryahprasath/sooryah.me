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

# 2. KPI ENDPOINT (Rolling 24h)
@app.get("/api/kpi")
def get_kpi():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        
        # 1. Unique Planes (Last 24h)
        q_unique = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "speed")
          |> group(columns: ["icao_hex"])
          |> count()
          |> group()
          |> count()
        '''
        
        # 2. Max Speed & Alt (Today)
        q_max = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "speed" or r["_field"] == "altitude")
          |> max()
        '''
        
        # Execute
        unique_res = query_api.query(org=INFLUX_ORG, query=q_unique)
        max_res = query_api.query(org=INFLUX_ORG, query=q_max)
        
        unique_count = 0
        if unique_res and len(unique_res) > 0 and len(unique_res[0].records) > 0:
            unique_count = unique_res[0].records[0].get_value()
            
        max_speed = 0
        max_alt = 0
        
        for table in max_res:
            for record in table.records:
                if record.get_field() == "speed": max_speed = record.get_value()
                if record.get_field() == "altitude": max_alt = record.get_value()

        return {
            "unique_planes_24h": unique_count,
            "max_speed_24h": f"{max_speed} kts",
            "max_alt_24h": f"{max_alt} ft"
        }
    except Exception as e:
        print(e)
        return {"unique_planes_24h": 0, "max_speed_24h": "0", "max_alt_24h": "0"}

# 3. SCATTER PLOT (Physics: Temp vs Altitude)
@app.get("/api/scatter")
def get_scatter():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Sample data: Get last 30 mins of raw points
        # Optimization: We only return valid temp/alt pairs
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30m)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "altitude" or r["_field"] == "temp_c")
          |> pivot(rowKey:["_time", "icao_hex"], columnKey: ["_field"], valueColumn: "_value")
          |> filter(fn: (r) => exists r.altitude and exists r.temp_c)
          |> keep(columns: ["altitude", "temp_c"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        data = []
        for table in result:
            for record in table.records:
                # Format for Chart.js Scatter: {x: temp, y: alt}
                data.append({"x": record["temp_c"], "y": record["altitude"]})
        return data
    except Exception:
        return []

# 4. POLAR CHART (Coverage)
@app.get("/api/polar")
def get_polar():
    try:
        client = get_influx_client()
        query_api = client.query_api()
        # Get Max Distance per 45-degree sector
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot")
          |> filter(fn: (r) => r["_field"] == "distance" or r["_field"] == "bearing")
          |> pivot(rowKey:["_time", "icao_hex"], columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["distance", "bearing"])
        '''
        result = query_api.query(org=INFLUX_ORG, query=query)
        
        # 8 Sectors (N, NE, E, SE, S, SW, W, NW)
        sectors = [0] * 8 
        for table in result:
            for record in table.records:
                b = record["bearing"]
                d = record["distance"]
                if b and d:
                    idx = int((b + 22.5) // 45) % 8
                    if d > sectors[idx]: sectors[idx] = d
                    
        return {"data": sectors}
    except Exception:
        return {"data": [0]*8}

# 5. GENERAL HISTORIES (Volume/Alt/Operators) - Keep existing logic
@app.get("/api/history")
def get_history():
    # ... (Keep existing code from previous step)
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
    labels, data = [], []
    for t in result:
        for r in t.records:
            labels.append(r.get_time().strftime("%H:%M"))
            data.append(round(r.get_value(), 1))
    return {"labels": labels, "data": data}

@app.get("/api/altitude")
def get_altitude():
    # ... (Keep existing code)
    client = get_influx_client()
    query_api = client.query_api()
    query = f'''from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot") |> filter(fn: (r) => r["_field"] == "altitude")'''
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

@app.get("/api/operators")
def get_operators():
    # ... (Keep existing code)
    client = get_influx_client()
    query_api = client.query_api()
    query = f'''from(bucket: "{INFLUX_BUCKET}") |> range(start: -30m) |> filter(fn: (r) => r["_measurement"] == "aircraft_snapshot") |> filter(fn: (r) => r["_field"] == "altitude") |> keep(columns: ["airline"])'''
    result = query_api.query(org=INFLUX_ORG, query=query)
    airlines = [r.values.get("airline", "Unknown") for t in result for r in t.records]
    counts = Counter(airlines).most_common(5)
    return {"labels": [x[0] for x in counts], "data": [x[1] for x in counts]}