from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.services.runway_engine import RunwayEngine

router = APIRouter(prefix="/api/v1/runway", tags=["Runway Engine"])
public_router = APIRouter(prefix="/api", tags=["Runway & Milestones Public API"])

async def runway_event_generator(emergency_overdrive: bool = False):
    engine = RunwayEngine()
    current_budget = 500.0
    fixed_cost = 10.0
    var_cost = 5.0
    
    # Just a simple loop to stream updates
    for _ in range(3):
        remaining_days = engine.calculate_remaining_days(
            current_budget, fixed_cost, var_cost, emergency_overdrive=emergency_overdrive
        )
        data = {
            "remaining_days": "Infinity" if remaining_days == float('inf') else remaining_days,
            "budget": current_budget,
            "daily_burn": fixed_cost + var_cost,
            "emergency_overdrive": emergency_overdrive,
            "status": "INVINCIBLE" if emergency_overdrive else "NORMAL"
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)

@router.get("/stream")
async def stream_runway(emergency_overdrive: bool = False):
    return StreamingResponse(
        runway_event_generator(emergency_overdrive=emergency_overdrive),
        media_type="text/event-stream"
    )

@public_router.get("/runway")
async def get_runway():
    engine = RunwayEngine()
    current_budget = 5140.0
    fixed_daily_cost = 80.0
    variable_daily_cost = 40.0
    remaining_days = engine.calculate_remaining_days(current_budget, fixed_daily_cost, variable_daily_cost)
    seconds_remaining = int(remaining_days * 86400)
    
    return {
        "days_remaining": int(remaining_days),
        "hours_remaining": int((remaining_days % 1) * 24),
        "seconds_remaining": seconds_remaining,
        "burn_rate_per_day": fixed_daily_cost + variable_daily_cost,
        "total_balance_thb": current_budget,
        "circuit_breaker_active": False,
        "emergency_overdrive": False,
        "budget_jars": [
            {
                "name": "Cloud Run Infrastructure",
                "percentage": 50,
                "allocated_thb": 2570,
                "description": "Backend API instances & async workers",
                "color": "from-blue-500 to-cyan-500",
            },
            {
                "name": "TMD Radar & Weather APIs",
                "percentage": 30,
                "allocated_thb": 1542,
                "description": "Radar image processing & storage",
                "color": "from-purple-500 to-indigo-500",
            },
            {
                "name": "Emergency Reserve Jar",
                "percentage": 20,
                "allocated_thb": 1028,
                "description": "Locked buffer for unexpected spikes",
                "color": "from-emerald-500 to-teal-500",
            },
        ],
    }

@public_router.get("/milestones")
async def get_milestones():
    is_locked = False
    try:
        import sqlite3, json, os
        db_path = "fonmayang.db"
        if not os.path.exists(db_path) and os.path.exists("../fonmayang.db"):
            db_path = "../fonmayang.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value_json FROM system_config WHERE key = 'milestone_lock'")
        row = cursor.fetchone()
        if row:
            val = json.loads(row[0])
            is_locked = (val == "true" or val is True)
        conn.close()
    except Exception:
        pass

    return {
        "target_thb": 10000,
        "current_thb": 10000 if is_locked else 5140,
        "is_locked": is_locked,
        "lock_reason": "Milestone 1 target (฿10,000 THB) reached. Donation automatically paused to prevent overfunding." if is_locked else None,
        "milestones": [
            {
                "id": 1,
                "title": "Milestone 1: 90-Day Server Fund",
                "target_thb": 10000,
                "current_thb": 10000 if is_locked else 5140,
                "completed": is_locked,
            }
        ],
    }
