import json
import httpx
import xmltodict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

TOKEN = "%22EAAAADYJ5m3QDK%2Fzk8Ac2lPcHMqXTt0%2BkZGyHEquAVooBDxraiDnWo0Eo0BFqFGx8uR0zGeGjDo%2Fs5BA25e9wUG4mf74L5fT6J%2Bv7uvlj3WqqAIgYkyaiXJL7I3n7RtCs%2BWomGBakFsvihBwHg2IWUb%2Fje5APgxRX2UBJ1IzLEP97DiaT6nGCk9b1b1dFqOSwwaWm1IEfmq6k0uHa12QgcC49c7qxxOmuB5oVJqLx%2Fo7wGmRDsOq3sW2CBGUl4jjzOpO6pV9pXHn%2B6bubfB1SB9F04VoDUgfX6e4RGHiyCf%2Bryoi7CZ5WcVoS1NaevCGe7ZnDkGTFWkBVg%2F4XElhkKZX7tAgemLaENBwQ08HP%2BUkn4ef%2Fmji5xtXzyqq4mdPq6pOOoH6xZ8KzzMtvhk5mM%2FLVK788iS3q4YFSZB1Y3SSVbx06Fjt2mL8InIHAjcaGcLG4vIg2RsKUyh2W%2B3q%2FX9E6GYeQ3tiltWq5dB%2FXCD2QXLk3gU6vlTp8cccyPIk99EJYH8JHPMY19zl709r6sVAy%2FW0JBWNGniL5VPRJFO7TJvV%22"
URL = f"https://live.financialjuice.com/FJService.asmx/Startup?info={TOKEN}&TimeOffset=7&tabID=0&oldID=0&TickerID=0&FeedCompanyID=0&strSearch=&extraNID=0"

state = {"headlines": [], "last_id": 0}

async def fetch_news():
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(URL)

    parsed = xmltodict.parse(response.text)
    data = json.loads(parsed["string"]["#text"])
    items = data["News"]

    fresh = [
        {
            "id": item["NewsID"],
            "title": item["Title"],
            "published": item["DatePublished"],
            "labels": item.get("Labels", []),
            "level": item.get("Level", ""),
            "url": item.get("EURL", ""),
            "breaking": "active-critical" in item.get("Level", ""),
        }
        for item in items
        if item["NewsID"] > state["last_id"]
    ]

    if fresh:
        state["headlines"] = fresh + state["headlines"]
        state["last_id"] = max(i["id"] for i in state["headlines"])

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await fetch_news()
    scheduler.add_job(fetch_news, "interval", seconds=60, id="fetch_job")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

@app.get("/news")
async def get_news():
    return state["headlines"]

@app.get("/news/breaking")
async def get_breaking_news():
    return [h for h in state["headlines"] if h["breaking"]]

@app.get("/status")
async def get_status():
    job = scheduler.get_job("fetch_job")
    if job and job.next_run_time:
        now = datetime.now(timezone.utc)
        seconds_remaining = max(0, (job.next_run_time - now).total_seconds())
        return {"next_fetch_in_seconds": round(seconds_remaining)}
    return {"next_fetch_in_seconds": None}