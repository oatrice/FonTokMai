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
async def get_runway(emergency_overdrive: bool = False):
    engine = RunwayEngine()
    current_budget = 5140.0
    fixed_daily_cost = 80.0
    variable_daily_cost = 40.0
    circuit_breaker_active = False
    is_overdrive = emergency_overdrive

    try:
        import sqlite3, json, os
        db_path = "fonmayang.db"
        if not os.path.exists(db_path) and os.path.exists("../fonmayang.db"):
            db_path = "../fonmayang.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value_json FROM system_config WHERE key = 'total_balance_thb'")
        row = cursor.fetchone()
        if row:
            current_budget = float(json.loads(row[0]))
            
        cursor.execute("SELECT value_json FROM system_config WHERE key = 'circuit_breaker_active'")
        row = cursor.fetchone()
        if row:
            val = json.loads(row[0])
            circuit_breaker_active = (val == "true" or val is True)

        cursor.execute("SELECT value_json FROM system_config WHERE key = 'emergency_overdrive'")
        row = cursor.fetchone()
        if row:
            val = json.loads(row[0])
            if val == "true" or val is True:
                is_overdrive = True

        cursor.execute("SELECT value_json FROM system_config WHERE key = 'burn_rate_per_day'")
        row = cursor.fetchone()
        if row:
            burn_rate = float(json.loads(row[0]))
            fixed_daily_cost = burn_rate * 0.66
            variable_daily_cost = burn_rate * 0.34
            
        conn.close()
    except Exception:
        pass

    remaining_days = engine.calculate_remaining_days(
        current_budget, fixed_daily_cost, variable_daily_cost, emergency_overdrive=is_overdrive
    )
    is_overdrive_active = is_overdrive or remaining_days == float('inf')
    
    jar_50 = int(current_budget * 0.50)
    jar_30 = int(current_budget * 0.30)
    jar_20 = int(current_budget * 0.20)

    return {
        "days_remaining": -1 if is_overdrive_active else int(remaining_days),
        "hours_remaining": -1 if is_overdrive_active else int((remaining_days % 1) * 24),
        "seconds_remaining": -1 if is_overdrive_active else int(remaining_days * 86400),
        "burn_rate_per_day": fixed_daily_cost + variable_daily_cost,
        "total_balance_thb": current_budget,
        "circuit_breaker_active": circuit_breaker_active,
        "emergency_overdrive": is_overdrive_active,
        "budget_jars": [
            {
                "name": "Cloud Run Infrastructure",
                "percentage": 50,
                "allocated_thb": jar_50,
                "description": "Backend API instances & async workers",
                "color": "from-blue-500 to-cyan-500",
            },
            {
                "name": "TMD Radar & Weather APIs",
                "percentage": 30,
                "allocated_thb": jar_30,
                "description": "Radar image processing & storage",
                "color": "from-purple-500 to-indigo-500",
            },
            {
                "name": "Emergency Reserve Jar",
                "percentage": 20,
                "allocated_thb": jar_20,
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
