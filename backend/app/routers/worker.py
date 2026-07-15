import os
from fastapi import APIRouter, Header, HTTPException, Depends
import logging
import traceback
from app.scheduler_tasks import (
    check_rain_and_alert,
    check_disasters_frequent_routine,
    check_disasters_infrequent_routine,
    fetch_tmd_radar_routine,
    trigger_mock_disaster
)

logger = logging.getLogger(__name__)

WORKER_SECRET = os.getenv("WORKER_SECRET", os.getenv("CRON_SECRET", "default_secret_for_local_testing"))

def verify_worker_secret(x_worker_secret: str = Header(None)):
    if not x_worker_secret or x_worker_secret != WORKER_SECRET:
        logger.warning("Unauthorized access to worker endpoint")
        raise HTTPException(status_code=401, detail="Unauthorized")

router = APIRouter(prefix="/worker", tags=["Worker"], dependencies=[Depends(verify_worker_secret)])

@router.post("/check-rain")
async def worker_check_rain():
    """Worker endpoint for predicting rain and sending alerts."""
    try:
        logger.info("Worker started: check-rain")
        await check_rain_and_alert()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed check-rain: {e}\n{traceback.format_exc()}")
        # Return 200 to prevent Cloud Tasks from infinite retry storms for non-transient API errors
        return {"status": "error", "message": str(e)}

@router.post("/check-disasters-frequent")
async def worker_check_disasters_frequent():
    """Worker endpoint for frequent disaster checks."""
    try:
        logger.info("Worker started: check-disasters-frequent")
        await check_disasters_frequent_routine()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed check-disasters-frequent: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/check-disasters-infrequent")
async def worker_check_disasters_infrequent():
    """Worker endpoint for infrequent disaster checks."""
    try:
        logger.info("Worker started: check-disasters-infrequent")
        await check_disasters_infrequent_routine()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed check-disasters-infrequent: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/fetch-tmd-radar")
async def worker_fetch_tmd_radar():
    """Worker endpoint for fetching TMD radar."""
    try:
        logger.info("Worker started: fetch-tmd-radar")
        await fetch_tmd_radar_routine()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed fetch-tmd-radar: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/trigger-mock-disaster")
async def worker_trigger_mock_disaster(payload: dict):
    """Worker endpoint to trigger a mock disaster."""
    try:
        logger.info("Worker started: trigger-mock-disaster")
        await trigger_mock_disaster(payload)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed trigger-mock-disaster: {e}")
        return {"status": "error", "message": str(e)}

from pydantic import BaseModel
from typing import Optional

class LocationPayload(BaseModel):
    chat_id: int
    lat: float
    lng: float
    force_endpoint: Optional[str] = None
    message_id_to_edit: Optional[int] = None
    show_advanced: bool = False
    message_id_to_edit: Optional[int] = None

@router.post("/process-telegram-location")
async def worker_process_telegram_location(payload: LocationPayload):
    try:
        from app.routers.webhook import process_telegram_location
        await process_telegram_location(
            payload.chat_id, payload.lat, payload.lng,
            payload.force_endpoint, payload.message_id_to_edit, payload.show_advanced
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed process-telegram-location: {e}")
        return {"status": "error", "message": str(e)}

class ChatIdPayload(BaseModel):
    chat_id: int

@router.post("/handle-mylocation")
async def worker_handle_mylocation(payload: ChatIdPayload):
    try:
        from app.routers.webhook import handle_mylocation_command
        await handle_mylocation_command(payload.chat_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_mylocation: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/handle-radar")
async def worker_handle_radar(payload: ChatIdPayload):
    try:
        from app.routers.webhook import handle_radar_command
        await handle_radar_command(payload.chat_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_radar: {e}")
        return {"status": "error", "message": str(e)}

class CommandPayload(BaseModel):
    chat_id: int
    command: str
    show_advanced: bool = False
    message_id_to_edit: Optional[int] = None

@router.post("/handle-rain")
async def worker_handle_rain(payload: CommandPayload):
    try:
        from app.routers.webhook import handle_rain_command
        await handle_rain_command(payload.chat_id, payload.command, payload.show_advanced, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_rain: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/handle-devmock")
async def worker_handle_devmock(payload: CommandPayload):
    try:
        from app.routers.webhook import handle_devmock_command
        await handle_devmock_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_devmock: {e}")
        return {"status": "error", "message": str(e)}


class CallbackPayload(BaseModel):
    callback_query: dict
    already_answered: bool = False

@router.post("/handle-callback")
async def worker_handle_callback(payload: CallbackPayload):
    try:
        from app.routers.webhook import handle_callback_query
        await handle_callback_query(payload.callback_query, payload.already_answered)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_callback: {e}")
        return {"status": "error", "message": str(e)}

class CommandWithMsgIdPayload(BaseModel):
    chat_id: int
    command: str
    message_id_to_edit: Optional[int] = None

@router.post("/handle-lock")
async def worker_handle_lock(payload: CommandWithMsgIdPayload):
    try:
        from app.routers.webhook import handle_lock_command
        await handle_lock_command(payload.chat_id, payload.command, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_lock: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/handle-unlock")
async def worker_handle_unlock(payload: CommandWithMsgIdPayload):
    try:
        from app.routers.webhook import handle_unlock_command
        await handle_unlock_command(payload.chat_id, payload.command, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_unlock: {e}")
        return {"status": "error", "message": str(e)}

class AdminCommandPayload(BaseModel):
    chat_id: int
    command: str
    username: str = ""
    message_id_to_edit: Optional[int] = None

@router.post("/handle-metrics")
async def worker_handle_metrics(payload: AdminCommandPayload):
    try:
        from app.routers.webhook import handle_metrics_command
        await handle_metrics_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_metrics: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/handle-setbudget")
async def worker_handle_setbudget(payload: AdminCommandPayload):
    try:
        from app.routers.webhook import handle_setbudget_command
        await handle_setbudget_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_setbudget: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/handle-tmd-fallback")
async def worker_handle_tmd_fallback(payload: AdminCommandPayload):
    try:
        from app.routers.webhook import handle_tmd_fallback_command
        await handle_tmd_fallback_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_tmd_fallback: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/handle-restore-public-access")
async def worker_handle_restore_public_access(payload: AdminCommandPayload):
    try:
        from app.routers.webhook import handle_restore_public_access_command
        await handle_restore_public_access_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_restore_public_access: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/handle-job")
async def worker_handle_job(payload: AdminCommandPayload):
    try:
        from app.routers.webhook import handle_job_command
        await handle_job_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Worker failed handle_job: {e}")
        return {"status": "error", "message": str(e)}

