import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.event_broadcaster import event_broadcaster

router = APIRouter(prefix="/api/v1/events", tags=["events"])

async def event_generator():
    queue = event_broadcaster.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                event_type = event.get("event")
                data = event.get("data")
                
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                yield "event: ping\n"
                yield "data: {}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        event_broadcaster.unsubscribe(queue)

@router.get("/stream")
async def stream_events():
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
