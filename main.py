from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from influxdb_client import InfluxDBClient
import httpx
import os

app = FastAPI()

# CONFIG
RADAR_IP = os.getenv("RADAR_IP")
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 1. LIVE PROXY (For the Map)
@app.get("/api/live")
async def get_live_radar():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://{RADAR_IP}:30053/ajax/aircraft", timeout=2.0)
            return resp.json()
        except:
            return {"aircraft": {}}

# 2. HISTORY API (For the Graph)
@app.get("/api/history")
def get_history():
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        query_api = client.query_api()
        
        # Query: Average aircraft count every 30 mins for last 24h
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
        
        # Parse result for Chart.js
        for table in result:
            for record in table.records:
                # Format time as HH:MM
                labels.append(record.get_time().strftime("%H:%M"))
                data.append(round(record.get_value(), 1))
                
        return {"labels": labels, "data": data}
    except Exception as e:
        print(f"Influx Query Error: {e}")
        return {"labels": [], "data": []}