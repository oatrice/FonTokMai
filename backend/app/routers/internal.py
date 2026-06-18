from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
import os
import logging
from app.dependencies import get_repo_context
from app.services.disaster_manager import process_disaster_event

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"]
)

INTERNAL_WEBHOOK_SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET", "dev_secret")

@router.post("/emsc-webhook")
async def emsc_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_internal_secret: str = Header(None)
):
    """
    Receive earthquake events from the standalone EMSC websocket worker.
    """
    if not x_internal_secret or x_internal_secret != INTERNAL_WEBHOOK_SECRET:
        logger.warning("Unauthorized access attempt to internal webhook.")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        event = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not event.get("id") or not event.get("lat"):
        logger.warning(f"Invalid event payload structure: {event}")
        raise HTTPException(status_code=400, detail="Missing required event fields")

    # Process the earthquake event in the background to avoid keeping the connection open
    async def process_event(event_data):
        try:
            logger.info(f"Processing internal EMSC earthquake event: {event_data.get('id')} at lat={event_data.get('lat')}, lng={event_data.get('lng')}")
            async with get_repo_context() as repo:
                await process_disaster_event(repo, "earthquake", event_data)
        except Exception as e:
            logger.error(f"Error processing internal EMSC earthquake event: {e}")

    background_tasks.add_task(process_event, event)

    return {"status": "ok", "message": "Event received and processing in background"}
