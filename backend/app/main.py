from dotenv import load_dotenv
load_dotenv()
import logging
from datetime import datetime, timezone

import re

class SensitiveDataFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.patterns = [
            (re.compile(r"(apikey=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(client_id=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(client_secret=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(/bot)[^/\s'\"]+", flags=re.IGNORECASE), r"\1***"),
        ]

    def filter(self, record):
        try:
            msg = record.getMessage()
            for pattern, replacement in self.patterns:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True

logging.basicConfig(level=logging.INFO)

# Apply filter to handlers
sensitive_filter = SensitiveDataFilter()
for handler in logging.root.handlers:
    handler.addFilter(sensitive_filter)

# Also explicitly add to httpx since it logs the URLs
logging.getLogger("httpx").addFilter(sensitive_filter)

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import weather, webhook, metrics

from contextlib import asynccontextmanager
from app.database import engine, Base
import app.models  # Ensure all models are registered before create_all

from app.scheduler_tasks import check_rain_and_alert
import os

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    from app.services.disaster_manager import process_disaster_event
    from app.dependencies import get_repo_context
    
    yield

app = FastAPI(
    title="FonMaYang (RainNowcast) API",
    description="Short-term rain prediction API (15-30 mins) with privacy-first and pluggable design.",
    version="1.0.0",
    lifespan=lifespan
)

from app.routers import weather, webhook, scheduler, metrics, worker, budget_webhook

app.include_router(weather.router)
app.include_router(webhook.router)
app.include_router(scheduler.router)
app.include_router(metrics.router)
app.include_router(worker.router)
app.include_router(budget_webhook.router)
from app.routers import internal
app.include_router(internal.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
