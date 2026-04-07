import json
import httpx
import xmltodict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

TOKEN = "%22EAAAAJeB7Sg8ttKJSHoB%2F5PQrYvJ%2B5H51pRU0Nkx57Af8e%2BzStX4nPwv%2BY3GH3MnC7LvhHxSnjj1ouffaWuldmwzgsKAXKluu0ZrbllFsV9AkavO%2BeHnBN581JbSnzY2w8NKnI5Gs8Oyquu%2FNJ2Qm9Ile7PjjRE%2FiKrEa1Y7qjzs0Q9fmZyb%2BuBNy4lMLG4hykjWXJvUL%2BFROlIqq19NycRIx9qq7SyvoYPTmZUbNnglr%2B3gv4CXUOJO6UxhC5QXL2Isp1ZVh9rc7TpUyBz4T8zCpmSBJLHts1ILR5pm0eCUZCqykln0iipRYL9yuzKoL%2BPI9lI35V%2FZZdjLKWcpp5TRrjuykCf80d%2BhYW7RNZsYVmGftDpdgoBQuShDbMhadQX%2F5ik5UohvDvKV066NflMvrOLAa55hqP7deFDZ15ZzyDBz9EEhkUs6e6ocXeS%2Bo%2FFGUqbl7xKxHcRZH1oCADClWLFscEc9CQAUtFWygnTdOXANWTNWd%2F47dQyFD3o7J24EKwUJyrRyOhJ%2BmyMEdytDSvo%3D%22&"
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
    scheduler.add_job(fetch_news, "interval", seconds=10, id="fetch_job")
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