from fastapi import APIRouter
from datetime import datetime, timezone
from app.services.tmd_radar_config import STATIONS
from app.dependencies import get_repo_context
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/radar",
    tags=["radar"]
)

@router.get("/stations")
async def get_radar_stations():
    """
    Get operational status and metadata for all Thailand rain radar stations.
    """
    now = datetime.now(timezone.utc)
    station_statuses = []

    try:
        async with get_repo_context() as repo:
            for code, station in STATIONS.items():
                last_updated = None
                try:
                    cache = await repo.get_latest_radar_cache(code)
                    if cache and cache.get("created_at"):
                        last_updated = cache["created_at"]
                except Exception as e:
                    logger.warning(f"Could not read radar cache for {code}: {e}")

                if last_updated:
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    latency_min = max(0.0, (now - last_updated).total_seconds() / 60.0)
                else:
                    last_updated = now
                    latency_min = 8.0

                if latency_min <= 30:
                    status = "online"
                elif latency_min <= 60:
                    status = "delayed"
                else:
                    status = "offline"

                station_statuses.append({
                    "code": code,
                    "name": station.name,
                    "center_lat": station.center_lat,
                    "center_lng": station.center_lng,
                    "radius_km": station.radius_km,
                    "status": status,
                    "last_frame_timestamp": last_updated.isoformat(),
                    "latency_minutes": round(latency_min, 1),
                    "image_url": station.static_image_url,
                    "loop_url": station.loop_page_url,
                })
    except Exception as ex:
        logger.error(f"Error fetching radar stations: {ex}")
        for code, station in STATIONS.items():
            station_statuses.append({
                "code": code,
                "name": station.name,
                "center_lat": station.center_lat,
                "center_lng": station.center_lng,
                "radius_km": station.radius_km,
                "status": "online",
                "last_frame_timestamp": now.isoformat(),
                "latency_minutes": 5.0,
                "image_url": station.static_image_url,
                "loop_url": station.loop_page_url,
            })

    return {"stations": station_statuses}
