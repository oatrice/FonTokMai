from fastapi import APIRouter, BackgroundTasks
import logging
from app.scheduler_tasks import (
    check_rain_and_alert,
    check_disasters_frequent_routine,
    check_disasters_infrequent_routine,
    fetch_tmd_radar_routine,
    trigger_mock_disaster
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/worker", tags=["Worker"])

@router.post("/check-rain")
async def worker_check_rain():
    """Worker endpoint for predicting rain and sending alerts."""
    logger.info("Worker started: check-rain")
    await check_rain_and_alert()
    return {"status": "ok"}

@router.post("/check-disasters-frequent")
async def worker_check_disasters_frequent():
    """Worker endpoint for frequent disaster checks."""
    logger.info("Worker started: check-disasters-frequent")
    await check_disasters_frequent_routine()
    return {"status": "ok"}

@router.post("/check-disasters-infrequent")
async def worker_check_disasters_infrequent():
    """Worker endpoint for infrequent disaster checks."""
    logger.info("Worker started: check-disasters-infrequent")
    await check_disasters_infrequent_routine()
    return {"status": "ok"}

@router.post("/fetch-tmd-radar")
async def worker_fetch_tmd_radar():
    """Worker endpoint for fetching TMD radar."""
    logger.info("Worker started: fetch-tmd-radar")
    await fetch_tmd_radar_routine()
    return {"status": "ok"}

@router.post("/trigger-mock-disaster")
async def worker_trigger_mock_disaster():
    """Worker endpoint to trigger a mock disaster."""
    logger.info("Worker started: trigger-mock-disaster")
    await trigger_mock_disaster()
    return {"status": "ok"}

from pydantic import BaseModel
from typing import Optional

class LocationPayload(BaseModel):
    chat_id: int
    lat: float
    lng: float
    force_endpoint: Optional[str] = None
    message_id_to_edit: Optional[int] = None
    show_advanced: bool = False

@router.post("/process-telegram-location")
async def worker_process_telegram_location(payload: LocationPayload):
    from app.routers.webhook import process_telegram_location
    await process_telegram_location(
        payload.chat_id, payload.lat, payload.lng,
        payload.force_endpoint, payload.message_id_to_edit, payload.show_advanced
    )
    return {"status": "ok"}

class ChatIdPayload(BaseModel):
    chat_id: int

@router.post("/handle-mylocation")
async def worker_handle_mylocation(payload: ChatIdPayload):
    from app.routers.webhook import handle_mylocation_command
    await handle_mylocation_command(payload.chat_id)
    return {"status": "ok"}

@router.post("/handle-radar")
async def worker_handle_radar(payload: ChatIdPayload):
    from app.routers.webhook import handle_radar_command
    await handle_radar_command(payload.chat_id)
    return {"status": "ok"}

class CommandPayload(BaseModel):
    chat_id: int
    command: str
    show_advanced: bool = False

@router.post("/handle-rain")
async def worker_handle_rain(payload: CommandPayload):
    from app.routers.webhook import handle_rain_command
    await handle_rain_command(payload.chat_id, payload.command, payload.show_advanced)
    return {"status": "ok"}

@router.post("/handle-devmock")
async def worker_handle_devmock(payload: CommandPayload):
    from app.routers.webhook import handle_devmock_command
    await handle_devmock_command(payload.chat_id, payload.command)
    return {"status": "ok"}

