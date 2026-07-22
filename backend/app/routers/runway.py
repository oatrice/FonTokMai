from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.services.runway_engine import RunwayEngine

router = APIRouter(prefix="/api/v1/runway", tags=["Runway Engine"])

async def runway_event_generator():
    engine = RunwayEngine()
    current_budget = 500.0
    fixed_cost = 10.0
    var_cost = 5.0
    
    # Just a simple loop to stream updates
    for _ in range(3):
        remaining_days = engine.calculate_remaining_days(current_budget, fixed_cost, var_cost)
        data = {
            "remaining_days": remaining_days,
            "budget": current_budget,
            "daily_burn": fixed_cost + var_cost
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)

@router.get("/stream")
async def stream_runway():
    return StreamingResponse(runway_event_generator(), media_type="text/event-stream")
