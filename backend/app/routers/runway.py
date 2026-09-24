import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json

from app.services.runway_engine import RunwayEngine
from app.database import get_db
from app.models import SystemConfig

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
async def get_runway(
    emergency_overdrive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    engine = RunwayEngine()
    current_budget = 5140.0
    fixed_daily_cost = 80.0
    variable_daily_cost = 40.0
    circuit_breaker_active = False
    is_overdrive = emergency_overdrive
    budget_percentages = {"infra": 50, "api": 30, "reserve": 20}
    balance_updated_at = None

    try:
        # 1. Total balance THB
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "total_balance_thb"))
        row = res.scalar_one_or_none()
        if row is not None:
            current_budget = float(json.loads(row))

        # 1.1 Balance updated_at timestamp (if tracked)
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "total_balance_updated_at"))
        row = res.scalar_one_or_none()
        if row is not None:
            balance_updated_at = float(json.loads(row))

        # 2. Circuit breaker active
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "circuit_breaker_active"))
        row = res.scalar_one_or_none()
        if row is not None:
            val = json.loads(row)
            circuit_breaker_active = (val == "true" or val is True)

        # 3. Emergency overdrive
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "emergency_overdrive"))
        row = res.scalar_one_or_none()
        if row is not None:
            val = json.loads(row)
            if val == "true" or val is True:
                is_overdrive = True

        # 4. Burn rate per day
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "burn_rate_per_day"))
        row = res.scalar_one_or_none()
        if row is not None:
            burn_rate = float(json.loads(row))
            fixed_daily_cost = burn_rate * 0.66
            variable_daily_cost = burn_rate * 0.34

        # 5. Dynamic Budget Jar Percentages
        res = await db.execute(select(SystemConfig.value_json).where(SystemConfig.key == "budget_jar_percentages"))
        row = res.scalar_one_or_none()
        if row is not None:
            parsed_percentages = json.loads(row)
            if isinstance(parsed_percentages, dict):
                budget_percentages.update(parsed_percentages)
    except Exception:
        pass

    now_ts = time.time()
    elapsed_days = 0.0
    if balance_updated_at is not None and now_ts > balance_updated_at:
        elapsed_days = (now_ts - balance_updated_at) / 86400.0

    remaining_days = engine.calculate_remaining_days(
        current_budget,
        fixed_daily_cost,
        variable_daily_cost,
        emergency_overdrive=is_overdrive,
        elapsed_days=elapsed_days,
    )
    is_overdrive_active = is_overdrive or remaining_days == float('inf')
    
    pct_infra = budget_percentages.get("infra", 50)
    pct_api = budget_percentages.get("api", 30)
    pct_reserve = budget_percentages.get("reserve", 20)

    # Dynamic remaining budget after elapsed burn
    total_burn = fixed_daily_cost + variable_daily_cost
    effective_balance = max(0.0, current_budget - (total_burn * elapsed_days)) if not is_overdrive_active else current_budget

    jar_infra = int(effective_balance * (pct_infra / 100.0))
    jar_api = int(effective_balance * (pct_api / 100.0))
    jar_reserve = int(effective_balance * (pct_reserve / 100.0))

    target_exhaustion_time = engine.calculate_target_exhaustion_time(
        remaining_days=remaining_days,
        base_timestamp=now_ts,
    )

    return {
        "days_remaining": -1 if is_overdrive_active else int(remaining_days),
        "hours_remaining": -1 if is_overdrive_active else int((remaining_days % 1) * 24),
        "seconds_remaining": -1 if is_overdrive_active else int(remaining_days * 86400),
        "target_exhaustion_time": target_exhaustion_time,
        "server_time": now_ts,
        "burn_rate_per_day": round(total_burn, 2),
        "total_balance_thb": round(effective_balance, 2),
        "circuit_breaker_active": circuit_breaker_active,
        "emergency_overdrive": is_overdrive_active,
        "budget_jars": [
            {
                "name": "Cloud Run Infrastructure",
                "percentage": pct_infra,
                "allocated_thb": jar_infra,
                "description": "Backend API instances & async workers",
                "color": "from-blue-500 to-cyan-500",
            },
            {
                "name": "TMD Radar & Weather APIs",
                "percentage": pct_api,
                "allocated_thb": jar_api,
                "description": "Radar image processing & storage",
                "color": "from-purple-500 to-indigo-500",
            },
            {
                "name": "Emergency Reserve Jar",
                "percentage": pct_reserve,
                "allocated_thb": jar_reserve,
                "description": "Locked buffer for unexpected spikes",
                "color": "from-emerald-500 to-teal-500",
            },
        ],
    }

