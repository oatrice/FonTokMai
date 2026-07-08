import os
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from app.services.cloud_tasks import CloudTasksService
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
        
    tasks_svc = CloudTasksService()
    task_name = await tasks_svc.enqueue_task("worker/check-rain", {})
    if not task_name:
        from app.scheduler_tasks import check_rain_and_alert
        background_tasks.add_task(check_rain_and_alert)
    return {"status": "ok", "message": "Rain check task enqueued"}

@router.post("/check-disasters-frequent")
async def trigger_disasters_frequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger frequent disaster checks (USGS Earthquakes)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    tasks_svc = CloudTasksService()
    task_name = await tasks_svc.enqueue_task("worker/check-disasters-frequent", {})
    if not task_name:
        from app.scheduler_tasks import check_disasters_frequent_routine
        background_tasks.add_task(check_disasters_frequent_routine)
    return {"status": "ok", "message": "Frequent disaster check task enqueued"}

@router.post("/check-disasters-infrequent")
async def trigger_disasters_infrequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger infrequent disaster checks (Xweather Cyclones/Fires)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    tasks_svc = CloudTasksService()
    task_name = await tasks_svc.enqueue_task("worker/check-disasters-infrequent", {})
    if not task_name:
        from app.scheduler_tasks import check_disasters_infrequent_routine
        background_tasks.add_task(check_disasters_infrequent_routine)
    return {"status": "ok", "message": "Infrequent disaster check task enqueued"}

@router.post("/fetch-tmd-radar")
async def trigger_fetch_tmd_radar(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to fetch and cache TMD Radar images to Firebase Storage."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    tasks_svc = CloudTasksService()
    task_name = await tasks_svc.enqueue_task("worker/fetch-tmd-radar", {})
    if not task_name:
        from app.scheduler_tasks import fetch_tmd_radar_routine
        background_tasks.add_task(fetch_tmd_radar_routine)
    return {"status": "ok", "message": "TMD Radar fetch task enqueued"}

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
        
    tasks_svc = CloudTasksService()
    task_name = await tasks_svc.enqueue_task("worker/trigger-mock-disaster", payload.model_dump())
    if not task_name:
        from app.scheduler_tasks import trigger_mock_disaster
        background_tasks.add_task(trigger_mock_disaster, payload.model_dump())
    return {"status": "ok", "message": f"Mock {payload.type} triggered"}
