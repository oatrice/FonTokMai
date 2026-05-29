import os
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from app.scheduler_tasks import check_rain_and_alert
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["scheduler"]
)

CRON_SECRET = os.getenv("CRON_SECRET", "default_secret_for_local_testing")

@router.post("/trigger-rain-check")
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
