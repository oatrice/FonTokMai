import os
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from app.scheduler_tasks import check_rain_and_alert
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cron",
    tags=["scheduler"]
)

CRON_SECRET = os.getenv("CRON_SECRET", "default_secret_for_local_testing")

@router.post("/check-rain")
async def trigger_rain_check(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """
    Endpoint for external schedulers (like Google Cloud Scheduler) to trigger the rain check.
    Must provide the correct X-Cron-Secret header.
    """
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        logger.warning("Unauthorized access to trigger-rain-check")
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    await check_rain_and_alert()
    return {"status": "ok", "message": "Rain check task completed"}

@router.post("/check-disasters-frequent")
async def trigger_disasters_frequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger frequent disaster checks (USGS Earthquakes)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.scheduler_tasks import check_disasters_frequent_routine
    await check_disasters_frequent_routine()
    return {"status": "ok", "message": "Frequent disaster check task completed"}

@router.post("/check-disasters-infrequent")
async def trigger_disasters_infrequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger infrequent disaster checks (Xweather Cyclones/Fires)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.scheduler_tasks import check_disasters_infrequent_routine
    await check_disasters_infrequent_routine()
    return {"status": "ok", "message": "Infrequent disaster check task completed"}

@router.post("/fetch-tmd-radar")
async def trigger_fetch_tmd_radar(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to fetch and cache TMD Radar images to Firebase Storage."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.scheduler_tasks import fetch_tmd_radar_routine
    # Run in background since uploading might take time
    background_tasks.add_task(fetch_tmd_radar_routine)
    return {"status": "ok", "message": "TMD Radar fetch task added to background"}

from pydantic import BaseModel
from typing import Optional

class MockDisasterPayload(BaseModel):
    type: str  # "earthquake", "cyclone", "fire"
    lat: float
    lng: float
    mag: Optional[float] = 7.0
    name: Optional[str] = "Custom Postman Disaster"

@router.post("/trigger-mock-disaster")
async def trigger_mock_disaster(payload: MockDisasterPayload, background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for developers to trigger a custom mock disaster event via tools like Postman."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    async def run_mock():
        import time
        from app.dependencies import get_repo_context
        from app.services.disaster_manager import process_disaster_event
        
        timestamp = int(time.time())
        event_id = f"postman_mock_{timestamp}"
        
        event_data = {
            "id": event_id,
            "lat": payload.lat,
            "lng": payload.lng,
        }
        
        if payload.type == "earthquake":
            event_data["mag"] = payload.mag
            event_data["place"] = payload.name
        elif payload.type == "cyclone":
            event_data["name"] = payload.name
            event_data["category"] = "Cat 4"
        elif payload.type == "fire":
            event_data["name"] = payload.name
            
        async with get_repo_context() as repo:
            await process_disaster_event(repo, payload.type, event_data)
            
    await run_mock()
    return {"status": "ok", "message": f"Mock {payload.type} triggered"}
