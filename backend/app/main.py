from dotenv import load_dotenv
load_dotenv()
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import weather, webhook

from contextlib import asynccontextmanager
from app.database import engine, Base

from app.scheduler_tasks import check_rain_and_alert
import os

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    from app.services.earthquake import start_emsc_websocket
    from app.services.disaster_manager import process_disaster_event
    from app.dependencies import get_repo_context
    
    async def ws_callback(event):
        async with get_repo_context() as repo:
            await process_disaster_event(repo, "earthquake", event)
            
    # Start the websocket in the background
    asyncio.create_task(start_emsc_websocket(ws_callback))
        
    yield

app = FastAPI(
    title="FonMaYang (RainNowcast) API",
    description="Short-term rain prediction API (15-30 mins) with privacy-first and pluggable design.",
    version="1.0.0",
    lifespan=lifespan
)

from app.routers import weather, webhook, scheduler

app.include_router(weather.router)
app.include_router(webhook.router)
app.include_router(scheduler.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
