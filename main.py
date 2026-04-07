import json
import httpx
import xmltodict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

TOKEN = "%22EAAAAFS4tDnbzY%2FmDSBUDo3SqolkRi4SMBfLlnwgO%2BLskGVRL7U00uS%2Fy%2FiJkafcBj1QvWcWaulNHnbvL%2BfUx1akYGcsjEgi1TPvkI%2BKep14eiic6g7DyGBiIOQr17CRjt9v9dLrBYNVbvs9Ff3JimwszEMfb9wvUHgWuRd1v11wPYp%2Fq2AaTzYu%2Fc6yIpBRR71mB6UNdG0TVHIITuWG3G%2FQEksZxewbeTlyiKj8X1BEtJPhRlqZMNUL4zy277Lpm1ClCTp5xONTMIbfHf8UCxvz%2FEfijnitWwPEG6YPB7RXrcApXAX7AFPaTQw6YeCfnBTAHfeKpW7YrGEd6J48CjMsFUNHQLM0tu78wuXm2DAhBlGk2stElRKULULMXGQ98oyoYBn5Ebs2UG3n%2F5%2BFuIPqRjTT%2FwLoKRofq%2FeehhnXQc8un8j%2Bk1pnvjeZ%2BvcuEiZh8T%2FBbBecHVgJ%2F%2FXq9mCYo0ZLaRpWqeO4qEN00hkEqaJzysIkWlU2WewDxk1bqpKTpEhJCoMW%2FBlni%2FLN%2BzPmz2xfT%2F1jwARkjaRPyHvKA6hv%22"
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