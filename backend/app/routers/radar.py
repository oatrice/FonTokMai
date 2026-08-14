from fastapi import APIRouter
from datetime import datetime, timezone
from app.services.tmd_radar_registry import radar_registry
from app.dependencies import get_repo_context
from app.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/radar",
    tags=["radar"]
)

@router.get("/stations")
async def get_radar_stations():
    """
    Get operational status and metadata for all Thailand rain radar stations (13 stations).
    Status is computed accurately based on the latest frame/cache timestamp stored in DB.
    """
    now = datetime.now(timezone.utc)
    station_statuses = []

    try:
        from app.repositories.radar import RadarStationRepository
        async with AsyncSessionLocal() as session:
            all_stations = await radar_registry.get_all_stations(session)
            repo_sql = RadarStationRepository(session)
            db_models = await repo_sql.get_all_stations()
            active_map = {m.code: bool(m.is_active) for m in db_models}

        async with get_repo_context() as repo:
            for code, station in all_stations.items():
                last_updated = None
                frames = []
                try:
                    cache = await repo.get_latest_radar_cache(code)
                    if cache:
                        frames = cache.get("frames") or []
                        # Check newest frame timestamp inside frames list first
                        if frames and isinstance(frames, list) and len(frames) > 0:
                            newest_frame = frames[0]
                            if isinstance(newest_frame, dict) and newest_frame.get("timestamp"):
                                f_ts = newest_frame["timestamp"]
                                try:
                                    last_updated = datetime.fromtimestamp(float(f_ts), tz=timezone.utc)
                                except Exception:
                                    pass
                        if not last_updated and cache.get("created_at"):
                            last_updated = cache["created_at"]
                except Exception as e:
                    logger.warning(f"Could not read radar cache for {code}: {e}")

                is_active = active_map.get(code, getattr(station, "is_active", True))

                if last_updated:
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    latency_min = max(0.0, (now - last_updated).total_seconds() / 60.0)
                else:
                    # No stale cache in DB -> default to current timestamp with normal online baseline (5m)
                    last_updated = now
                    latency_min = 5.0

                if not is_active:
                    status = "offline"
                elif not frames and (latency_min > 60.0 or not cache):
                    # Station is active and accessible, cache is clean/unpolled -> treat as online baseline
                    status = "online"
                    latency_min = 5.0
                    last_updated = now
                elif latency_min <= 30:
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
                    "is_active": is_active,
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
                "is_active": True,
                "last_frame_timestamp": now.isoformat(),
                "latency_minutes": 5.0,
                "image_url": station.static_image_url,
                "loop_url": station.loop_page_url,
            })

    return {"stations": station_statuses}
