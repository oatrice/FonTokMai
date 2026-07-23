import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
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
        
        # Dynamically add manual tracking columns to user_locations if they do not exist
        from sqlalchemy import text
        for col_name, col_type in [
            ("tracking_mode", "VARCHAR DEFAULT 'auto' NOT NULL"),
            ("locked_target_id", "VARCHAR"),
            ("locked_target_cx", "INTEGER"),
            ("locked_target_cy", "INTEGER"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE user_locations ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass
                
        # Dynamically add source column to radar_latest_cache if it does not exist
        try:
            await conn.execute(text("ALTER TABLE radar_latest_cache ADD COLUMN source VARCHAR DEFAULT 'api'"))
        except Exception:
            pass
        
    from app.services.disaster_manager import process_disaster_event
    from app.dependencies import get_repo_context
    from app.services.weather_manager import _DEV_CONFIG

    # Load global dev config from repository
    async with get_repo_context() as repo:
        try:
            config = await repo.get_global_dev_config()
            if config:
                for k, v in config.items():
                    if k in _DEV_CONFIG:
                        _DEV_CONFIG[k] = v
        except Exception as e:
            logging.error(f"Failed to load global dev config: {e}")
    
    # Setup Telegram bot commands on startup
    from app.services.telegram import setup_telegram_commands
    try:
        await setup_telegram_commands()
    except Exception as e:
        logging.error(f"Failed to setup Telegram commands during startup: {e}")
    
    yield
    from app.dependencies import close_http_client
    await close_http_client()

app = FastAPI(
    title="FonMaYang (RainNowcast) API",
    description="Short-term rain prediction API (15-30 mins) with privacy-first and pluggable design.",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
]

# Allow custom Vercel origin via env var if configured
if os.getenv("ALLOWED_ORIGIN"):
    allowed_origins.append(os.getenv("ALLOWED_ORIGIN"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for API rewrites and cross-origin fetch
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
import json
from app.routers.webhook_utils import log_audit_event
from app.services.command_router import router as cmd_router
from app.services.telegram import DEVELOPER_CHAT_IDS

@app.middleware("http")
async def telegram_webhook_audit_middleware(request: Request, call_next):
    # Only run for the Telegram webhook endpoint
    if request.url.path == "/api/v1/telegram/webhook" and request.method == "POST":
        try:
            body = await request.body()
            # Cache the body in memory to allow downstream handlers to read it again
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive
            
            payload = json.loads(body)
            if "message" in payload:
                message = payload["message"]
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")
                username = message.get("from", {}).get("username", "")
                
                if text and chat_id:
                    match_result = cmd_router.match(text)
                    if match_result:
                        prefix, config = match_result
                        if config.get("audit_log"):
                            dev_ids = set(str(did) for did in DEVELOPER_CHAT_IDS)
                            if str(chat_id) not in dev_ids:
                                log_audit_event("admin_command_executed", chat_id, username, {"command": text})
        except Exception as e:
            logging.error(f"Error in telegram_webhook_audit_middleware: {e}")
            
    return await call_next(request)

from app.routers import weather, webhook, scheduler, metrics, worker, budget_webhook, line_webhook, auth, runway, stripe_webhook, milestones

app.include_router(weather.router)
app.include_router(webhook.router)
app.include_router(scheduler.router)
app.include_router(metrics.router)
app.include_router(worker.router)
app.include_router(budget_webhook.router)
app.include_router(line_webhook.router)
app.include_router(auth.router)
app.include_router(runway.router)
app.include_router(runway.public_router)
app.include_router(stripe_webhook.router)
app.include_router(milestones.router)
from app.routers import internal
app.include_router(internal.router)
 
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static/temp_media", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}
