import sys
import types
# Workaround for Python 3.14 protobuf / google._upb C-API incompatibility
sys.modules.setdefault("google._upb", types.ModuleType("google._upb"))
sys.modules["google._upb._message"] = None

import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
from dotenv import load_dotenv
load_dotenv()
import logging
from datetime import datetime, timezone

import re

from sqlalchemy import inspect, text


USER_LOCATION_SCHEMA_COLUMNS = (
    ("name", "VARCHAR DEFAULT 'default' NOT NULL"),
    ("last_alert_max_rain", "FLOAT DEFAULT 0.0"),
    ("tracking_mode", "VARCHAR DEFAULT 'auto' NOT NULL"),
    ("locked_target_id", "VARCHAR"),
    ("locked_target_cx", "INTEGER"),
    ("locked_target_cy", "INTEGER"),
    ("is_snoozed", "BOOLEAN DEFAULT FALSE NOT NULL"),
    ("snooze_until", "TIMESTAMP"),
    ("presence_policy", "VARCHAR DEFAULT 'always_ask' NOT NULL"),
    ("schedule_active_days", "VARCHAR"),
    ("schedule_active_start", "VARCHAR"),
    ("schedule_active_end", "VARCHAR"),
    ("presence_answer_ttl_minutes", "INTEGER DEFAULT 120 NOT NULL"),
    ("default_fallback_policy", "VARCHAR DEFAULT 'notify' NOT NULL"),
)

RADAR_LATEST_CACHE_SCHEMA_COLUMNS = (
    ("source", "VARCHAR DEFAULT 'api'"),
)

SYSTEM_USAGE_EVENTS_SCHEMA_COLUMNS = (
    ("event_category", "VARCHAR DEFAULT 'proactive_alert' NOT NULL"),
    ("command_name", "VARCHAR"),
    ("is_mock", "BOOLEAN DEFAULT FALSE NOT NULL"),
)


class SensitiveDataFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.patterns = [
            (re.compile(r"(apikey=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(client_id=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(client_secret=)[^&\s'\"]+", flags=re.IGNORECASE), r"\1***"),
            (re.compile(r"(/bot)[^/\s'\"]+", flags=re.IGNORECASE), r"\1***"),
        ]

    def _sanitize(self, value):
        if isinstance(value, str):
            for pattern, replacement in self.patterns:
                value = pattern.sub(replacement, value)
            return value
        if isinstance(value, tuple):
            return tuple(self._sanitize(item) for item in value)
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, dict):
            return {
                key: self._sanitize(item)
                for key, item in value.items()
            }
        return value

    def filter(self, record):
        try:
            record.msg = self._sanitize(record.msg)
            record.args = self._sanitize(record.args)
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

def setup_file_logging(log_file_path: str = None) -> logging.Handler | None:
    """Configures a RotatingFileHandler for application logging."""
    from logging.handlers import RotatingFileHandler
    
    target_path = log_file_path or os.getenv("LOG_FILE_PATH", "logs/backend.log")
    if not target_path or not target_path.strip():
        return None
        
    try:
        log_dir = os.path.dirname(target_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = RotatingFileHandler(
            target_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        
        logging.root.addHandler(file_handler)
        # Also attach to uvicorn loggers so access and error logs go to file
        for uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            u_logger = logging.getLogger(uvicorn_logger_name)
            u_logger.addHandler(file_handler)
            u_logger.addFilter(sensitive_filter)
            
        return file_handler
    except Exception as e:
        logging.warning("Failed to initialize file logging at %s: %s", target_path, e)
        return None

# Initialize file logging if configured or default to logs/backend.log
setup_file_logging()

logging.info(
    "Backend env loaded: ENVIRONMENT=%s FORCE_GCP_REAL_DATA=%s DATABASE_URL=%s",
    os.getenv("ENVIRONMENT", "development"),
    os.getenv("FORCE_GCP_REAL_DATA", ""),
    "set" if os.getenv("DATABASE_URL") else "missing",
)

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import weather, webhook, metrics
from app.routers.admin_radar import router as admin_radar_router

from contextlib import asynccontextmanager
from app.database import engine, Base, AsyncSessionLocal
import app.models  # Ensure all models are registered before create_all

from app.scheduler_tasks import check_rain_and_alert
import os

import asyncio

def ensure_schema_migrations(connection):
    inspector = inspect(connection)
    
    if inspector.has_table("alert_notification_log") and not inspector.has_table("system_usage_events"):
        connection.execute(text('ALTER TABLE "alert_notification_log" RENAME TO "system_usage_events"'))
        
    for table_name, columns in (
        ("user_locations", USER_LOCATION_SCHEMA_COLUMNS),
        ("radar_latest_cache", RADAR_LATEST_CACHE_SCHEMA_COLUMNS),
        ("system_usage_events", SYSTEM_USAGE_EVENTS_SCHEMA_COLUMNS),
    ):
        if not inspector.has_table(table_name):
            continue

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }
        for column_name, column_type in columns:
            if column_name in existing_columns:
                continue
            connection.execute(
                text(
                    f'ALTER TABLE "{table_name}" '
                    f'ADD COLUMN "{column_name}" {column_type}'
                )
            )
            existing_columns.add(column_name)

    if inspector.has_table("system_usage_events"):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("system_usage_events")}
        if "ix_usage_events_date_mock_cat" not in existing_indexes:
            try:
                connection.execute(
                    text('CREATE INDEX IF NOT EXISTS "ix_usage_events_date_mock_cat" ON "system_usage_events" ("alerted_at", "is_mock", "event_category")')
                )
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(ensure_schema_migrations)

        # Automatic Seed Initial system_config settings if not already present
        async with AsyncSessionLocal() as session:
            from sqlalchemy.future import select
            from app.models import SystemConfig
            import json
            
            seeds = {
                "total_balance_thb": "25140.0",
                "burn_rate_per_day": "120.0",
                "budget_jar_percentages": json.dumps({"infra": 50, "api": 30, "reserve": 20}),
                "circuit_breaker_active": "false",
                "emergency_overdrive": "false",
                "gcp_force_real_data": "true" if os.getenv("ENVIRONMENT", "development").lower() in {"staging", "production", "prod", "main"} else "false",
            }
            
            for key, val in seeds.items():
                stmt = select(SystemConfig).where(SystemConfig.key == key)
                res = await session.execute(stmt)
                if res.scalar_one_or_none() is None:
                    session.add(SystemConfig(key=key, value_json=val))
            
            # Seed Initial Radar Stations into DB if empty
            from app.repositories.radar import RadarStationRepository
            from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
            radar_repo = RadarStationRepository(session)
            existing_stations = await radar_repo.get_all_stations()
            if not existing_stations:
                logging.info(f"Seeding {len(KNOWN_TMD_RADAR_PRESETS)} initial radar stations into DB...")
                for preset in KNOWN_TMD_RADAR_PRESETS:
                    await radar_repo.upsert_station(preset)
            await session.commit()
    except Exception as e:
        logging.error(f"Failed to initialize database tables during startup: {e}")
        
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
    
    # Setup Telegram bot commands on startup (non-blocking)
    from app.services.telegram import setup_telegram_commands
    asyncio.create_task(setup_telegram_commands())
    
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

from app.routers import weather, webhook, scheduler, metrics, worker, budget_webhook, line_webhook, auth, runway, stripe_webhook, milestones, financial, events, donations, radar, locations

app.include_router(weather.router)
app.include_router(radar.router)
app.include_router(webhook.router)
app.include_router(scheduler.router)
app.include_router(metrics.router)
app.include_router(admin_radar_router, prefix="/api/v1/admin/radar")
app.include_router(locations.router)
app.include_router(worker.router)
app.include_router(budget_webhook.router)
app.include_router(line_webhook.router)
app.include_router(auth.router)
app.include_router(runway.router)
app.include_router(runway.public_router)
app.include_router(stripe_webhook.router)
app.include_router(milestones.router)
app.include_router(financial.router)
app.include_router(events.router)
app.include_router(donations.router)
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
    version = "unknown"
    try:
        # Check one level up (if running from backend/)
        with open("../VERSION", "r") as f:
            version = f.read().strip()
    except Exception:
        try:
            # Check current directory (if running from root)
            with open("VERSION", "r") as f:
                version = f.read().strip()
        except Exception:
            pass
            
    environment = os.getenv("ENVIRONMENT", "development")
    commit_sha = os.getenv("COMMIT_SHA", "local")
    
    return {
        "status": "ok", 
        "version": version, 
        "environment": environment, 
        "commit_sha": commit_sha
    }
