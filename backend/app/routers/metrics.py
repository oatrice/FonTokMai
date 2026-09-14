import os
import io
import csv
import json
import secrets
from dataclasses import asdict
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, Response

from app.dependencies import get_repo_context
from app.services.metrics_service import MetricsService
from app.services.gcp_billing import GCPBillingService

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["metrics"]
)


@router.get("/export")
async def export_metrics(
    days: int = 7,
    format: str = "json",
    routine: Optional[str] = None,
    x_cron_secret: str = Header(None)
):
    """
    Endpoint สำหรับดึง Cloud Run Dashboard Metrics แบบ Lightweight
    - days: ดึงข้อมูลย้อนหลังกี่วัน (default 7)
    - format: json (default) หรือ csv (เหมาะสำหรับ import เข้า Google Sheets)
    - routine: (optional) ระบุชื่อ routine หากต้องการกรองเฉพาะ routine นั้น
    """
    server_secret = os.getenv("CRON_SECRET")
    if not server_secret or not x_cron_secret or not secrets.compare_digest(x_cron_secret, server_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with get_repo_context() as repo:
        if format == "csv":
            # For CSV, we return raw logs, not aggregated summary
            logs = await repo.get_cron_metrics(days=days, routine_name=routine)
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "routine_name", 
                "run_at", 
                "duration_s", 
                "alerts_sent", 
                "locations_checked", 
                "errors",
                "extra_data"
            ])
            
            for log in logs:
                extra = ""
                if log.get("extra_data"):
                    try:
                        extra = json.dumps(log["extra_data"]) if isinstance(log["extra_data"], dict) else str(log["extra_data"])
                    except:
                        pass
                        
                writer.writerow([
                    log.get("routine_name", ""),
                    log.get("run_at").isoformat() if log.get("run_at") else "",
                    f"{log.get('duration_s', 0.0):.2f}",
                    log.get("alerts_sent", 0),
                    log.get("locations_checked", 0),
                    log.get("errors", 0),
                    extra
                ])
                
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=cron_metrics.csv"}
            )
            
        else:
            # JSON summary format
            service = MetricsService(repo=repo)
            summary = await service.get_metrics_summary(days=days)
            
            if routine and routine in summary["routines"]:
                # Filter just to requested routine
                summary["routines"] = {routine: summary["routines"][routine]}
            elif routine:
                summary["routines"] = {}
                
            return JSONResponse(content=summary)

@router.get("/queue")
async def get_queue_status(
    x_cron_secret: str = Header(None)
):
    """
    Endpoint สำหรับดึง Cloud Tasks Queue Depth ปัจจุบัน
    """
    server_secret = os.getenv("CRON_SECRET")
    if not server_secret or not x_cron_secret or not secrets.compare_digest(x_cron_secret, server_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.services.cloud_tasks import CloudTasksService
    import time
    
    tasks_svc = CloudTasksService()
    start_time = time.time()
    queue_metrics = await tasks_svc.get_queue_metrics()
    duration_ms = int((time.time() - start_time) * 1000)
    
    queue_metrics["query_duration_ms"] = duration_ms
    queue_metrics["timestamp"] = int(time.time())
    
    return JSONResponse(content=queue_metrics)


@router.get("/gcp-costs")
async def get_gcp_costs(
    period: str = "current_month",
    x_cron_secret: str = Header(None)
):
    """
    Fetch GCP infrastructure costs broken down by service.

    Query parameters:
      period: 'current_month' (default), 'last_month', '30d', '7d'

    Returns mock data transparently when GCP credentials are not configured.
    Requires x-cron-secret header for authentication.
    """
    server_secret = os.getenv("CRON_SECRET")
    if (
        not server_secret
        or not x_cron_secret
        or not secrets.compare_digest(x_cron_secret, server_secret)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    svc = GCPBillingService()
    require_real_data = await svc.resolve_force_real_data()

    if require_real_data:
        breakdown = svc.get_current_month_costs(period=period, require_real_data=True)
    else:
        breakdown = svc.get_current_month_costs(period=period)
    return JSONResponse(content=asdict(breakdown))


@router.get("/monthly")
async def get_monthly_metrics(month: Optional[str] = None):
    """
    Monthly Alert Accuracy Metrics (Issue #292, #293):
    Returns aggregated stats and daily breakdown for the requested month ('YYYY-MM').
    Defaults to current UTC month.
    """
    import datetime
    from app.database import AsyncSessionLocal
    from app.models import SystemUsageEvent
    from sqlalchemy.future import select
    from sqlalchemy import func

    if not month:
        now = datetime.datetime.now(datetime.timezone.utc)
        month = now.strftime("%Y-%m")

    try:
        start_date = datetime.datetime.strptime(f"{month}-01", "%Y-%m-%d")
        # Compute end date (first day of next month)
        if start_date.month == 12:
            end_date = datetime.datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime.datetime(start_date.year, start_date.month + 1, 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format, expected YYYY-MM")

    async with AsyncSessionLocal() as session:
        stmt = select(SystemUsageEvent).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False,
            SystemUsageEvent.event_category == "proactive_alert"
        )
        res = await session.execute(stmt)
        logs = res.scalars().all()

        total_alerts = len(logs)
        false_alarms_user = sum(1 for l in logs if l.user_feedback_result == "false_alarm")
        false_alarms_auto = sum(1 for l in logs if l.auto_verify_result == "false_alarm")
        # Combined false alarms count (unique alert IDs that were false alarms by user or auto)
        false_alarms_total = sum(1 for l in logs if l.user_feedback_result == "false_alarm" or l.auto_verify_result == "false_alarm")
        true_alarms = total_alerts - false_alarms_total

        false_alarm_rate_pct = round((false_alarms_total / total_alerts) * 100.0, 1) if total_alerts > 0 else 0.0

        # Daily breakdown for charting
        daily_map = {}
        for l in logs:
            day_str = l.alerted_at.strftime("%Y-%m-%d")
            if day_str not in daily_map:
                daily_map[day_str] = {"date": day_str, "total": 0, "true_alarm": 0, "false_alarm": 0}
            daily_map[day_str]["total"] += 1
            if l.user_feedback_result == "false_alarm" or l.auto_verify_result == "false_alarm":
                daily_map[day_str]["false_alarm"] += 1
            else:
                daily_map[day_str]["true_alarm"] += 1

        daily_breakdown = sorted(daily_map.values(), key=lambda x: x["date"])

        return {
            "month": month,
            "total_alerts": total_alerts,
            "true_alarms": true_alarms,
            "false_alarms_total": false_alarms_total,
            "false_alarms_user": false_alarms_user,
            "false_alarms_auto": false_alarms_auto,
            "false_alarm_rate_pct": false_alarm_rate_pct,
            "daily_breakdown": daily_breakdown
        }


@router.get("/cost")
async def get_monthly_cost(month: Optional[str] = None):
    """
    Monthly Infrastructure & Unit Economics Cost (Issue #292, #293):
    GCP + External Costs, Cost per Alert, Cost per True Alert.
    """
    import datetime
    from app.database import AsyncSessionLocal
    from app.models import ExternalCostConfig, SystemUsageEvent
    from sqlalchemy.future import select

    if not month:
        now = datetime.datetime.now(datetime.timezone.utc)
        month = now.strftime("%Y-%m")

    # 1. Fetch GCP cost
    gcp_svc = GCPBillingService()
    try:
        gcp_breakdown = gcp_svc.get_current_month_costs(period="current_month")
        gcp_cost_thb = float(gcp_breakdown.total_thb)
    except Exception:
        gcp_cost_thb = 0.0

    # 2. Fetch external costs
    async with AsyncSessionLocal() as session:
        stmt = select(ExternalCostConfig).where(ExternalCostConfig.month == month)
        res = await session.execute(stmt)
        ext_configs = res.scalars().all()
        external_cost_thb = sum(c.amount_thb for c in ext_configs)

        # Baseline fallback for external cost if none configured (default proxy pool estimate)
        if external_cost_thb == 0.0:
            external_cost_thb = 150.0 # Standard proxy baseline

        total_cost_thb = round(gcp_cost_thb + external_cost_thb, 2)

        # 3. Calculate Unit Economics
        start_date = datetime.datetime.strptime(f"{month}-01", "%Y-%m-%d")
        if start_date.month == 12:
            end_date = datetime.datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime.datetime(start_date.year, start_date.month + 1, 1)

        stmt_alerts = select(SystemUsageEvent).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False
        )
        res_alerts = await session.execute(stmt_alerts)
        logs = res_alerts.scalars().all()
        
        proactive_count = sum(1 for l in logs if l.event_category == "proactive_alert")
        ondemand_count = sum(1 for l in logs if l.event_category == "ondemand_query")
        total_system_usage = proactive_count + ondemand_count

        cost_per_proactive_alert = 0.0
        cost_per_ondemand_query = 0.0
        
        if total_system_usage > 0:
            cost_per_proactive_alert = round((total_cost_thb * (proactive_count / total_system_usage)) / proactive_count, 2) if proactive_count > 0 else 0.0
            cost_per_ondemand_query = round((total_cost_thb * (ondemand_count / total_system_usage)) / ondemand_count, 2) if ondemand_count > 0 else 0.0

        unique_users = len(set(l.chat_id for l in logs))
        blended_cost_per_active_user = round(total_cost_thb / unique_users, 2) if unique_users > 0 else 0.0

        # Preserve legacy fields for backward compatibility if needed by older dashboards
        cost_per_alert = round(total_cost_thb / total_system_usage, 2) if total_system_usage > 0 else 0.0

        return {
            "month": month,
            "gcp_cost_thb": gcp_cost_thb,
            "external_cost_thb": external_cost_thb,
            "total_cost_thb": total_cost_thb,
            "total_alerts": total_system_usage,
            "cost_per_alert": cost_per_alert,
            "cost_per_proactive_alert": cost_per_proactive_alert,
            "cost_per_ondemand_query": cost_per_ondemand_query,
            "blended_cost_per_active_user": blended_cost_per_active_user,
            "proactive_count": proactive_count,
            "ondemand_count": ondemand_count,
            "mau_count": unique_users
        }

