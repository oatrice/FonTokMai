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
        
    background_tasks.add_task(check_rain_and_alert)
    return {"status": "ok", "message": "Rain check task added to background"}

@router.post("/check-disasters-frequent")
async def trigger_disasters_frequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger frequent disaster checks (USGS Earthquakes)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.scheduler_tasks import check_disasters_frequent_routine
    background_tasks.add_task(check_disasters_frequent_routine)
    return {"status": "ok", "message": "Frequent disaster check task added to background"}

@router.post("/check-disasters-infrequent")
async def trigger_disasters_infrequent(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Endpoint for external schedulers to trigger infrequent disaster checks (Xweather Cyclones/Fires)."""
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.scheduler_tasks import check_disasters_infrequent_routine
    background_tasks.add_task(check_disasters_infrequent_routine)
    return {"status": "ok", "message": "Infrequent disaster check task added to background"}
