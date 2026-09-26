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
    force_refresh: bool = False,
    x_cron_secret: str = Header(None)
):
    """
    Fetch GCP infrastructure costs broken down by service with in-memory caching and DB archiving.

    Query parameters:
      period: 'current_month' (default), 'last_month', '30d', '7d', or 'YYYY-MM'
      force_refresh: bypass cache and force re-query BigQuery if True

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

    breakdown = await svc.get_costs_with_archive(
        period=period,
        require_real_data=require_real_data,
        force_refresh=force_refresh,
    )
    return JSONResponse(content=asdict(breakdown))



def _get_month_date_range(month: Optional[str] = None):
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    target_month = month or now.strftime("%Y-%m")
    try:
        start_date = datetime.datetime.strptime(f"{target_month}-01", "%Y-%m-%d")
        if start_date.month == 12:
            end_date = datetime.datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime.datetime(start_date.year, start_date.month + 1, 1)
        return target_month, start_date, end_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format, expected YYYY-MM")


@router.get("/monthly")
async def get_monthly_metrics(month: Optional[str] = None):
    """
    Monthly Alert Accuracy Metrics (Issue #292, #293):
    Returns aggregated stats and daily breakdown for the requested month ('YYYY-MM').
    Defaults to current UTC month.
    """
    from app.database import AsyncSessionLocal
    from app.models import SystemUsageEvent
    from sqlalchemy.future import select
    from sqlalchemy import func, case

    target_month, start_date, end_date = _get_month_date_range(month)

    async with AsyncSessionLocal() as session:
        # Aggregated totals query
        stmt_summary = select(
            func.count(SystemUsageEvent.id).label("total_alerts"),
            func.coalesce(func.sum(case((SystemUsageEvent.user_feedback_result == "false_alarm", 1), else_=0)), 0).label("false_alarms_user"),
            func.coalesce(func.sum(case((SystemUsageEvent.auto_verify_result == "false_alarm", 1), else_=0)), 0).label("false_alarms_auto"),
            func.coalesce(func.sum(case(((SystemUsageEvent.user_feedback_result == "false_alarm") | (SystemUsageEvent.auto_verify_result == "false_alarm"), 1), else_=0)), 0).label("false_alarms_total"),
        ).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False,
            SystemUsageEvent.event_category == "proactive_alert"
        )
        summary_res = await session.execute(stmt_summary)
        row = summary_res.one()
        total_alerts = int(row.total_alerts or 0)
        false_alarms_user = int(row.false_alarms_user or 0)
        false_alarms_auto = int(row.false_alarms_auto or 0)
        false_alarms_total = int(row.false_alarms_total or 0)
        true_alarms = total_alerts - false_alarms_total
        false_alarm_rate_pct = round((false_alarms_total / total_alerts) * 100.0, 1) if total_alerts > 0 else 0.0

        # Daily breakdown query
        stmt_daily = select(
            func.date(SystemUsageEvent.alerted_at).label("day_str"),
            func.count(SystemUsageEvent.id).label("total"),
            func.coalesce(func.sum(case(((SystemUsageEvent.user_feedback_result == "false_alarm") | (SystemUsageEvent.auto_verify_result == "false_alarm"), 1), else_=0)), 0).label("false_alarm")
        ).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False,
            SystemUsageEvent.event_category == "proactive_alert"
        ).group_by(func.date(SystemUsageEvent.alerted_at)).order_by(func.date(SystemUsageEvent.alerted_at))
        daily_res = await session.execute(stmt_daily)
        daily_breakdown = []
        for d in daily_res.all():
            d_total = int(d.total or 0)
            d_fa = int(d.false_alarm or 0)
            daily_breakdown.append({
                "date": str(d.day_str),
                "total": d_total,
                "true_alarm": d_total - d_fa,
                "false_alarm": d_fa
            })

        return {
            "month": target_month,
            "total_alerts": total_alerts,
            "true_alarms": true_alarms,
            "false_alarms_total": false_alarms_total,
            "false_alarms_user": false_alarms_user,
            "false_alarms_auto": false_alarms_auto,
            "false_alarm_rate_pct": false_alarm_rate_pct,
            "daily_breakdown": daily_breakdown
        }


def _get_year_date_range(year: Optional[str] = None):
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    target_year = year or now.strftime("%Y")
    try:
        y = int(target_year)
        start_date = datetime.datetime(y, 1, 1)
        end_date = datetime.datetime(y + 1, 1, 1)
        return str(y), start_date, end_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid year format, expected YYYY")


@router.get("/yearly")
async def get_yearly_metrics(year: Optional[str] = None):
    """
    Yearly Alert Accuracy Metrics:
    Returns aggregated stats and 12-month breakdown for the requested year ('YYYY').
    Defaults to current UTC year.
    """
    from app.database import AsyncSessionLocal
    from app.models import SystemUsageEvent
    from sqlalchemy.future import select
    from sqlalchemy import func, case

    target_year, start_date, end_date = _get_year_date_range(year)

    async with AsyncSessionLocal() as session:
        # Aggregated totals query for the entire year
        stmt_summary = select(
            func.count(SystemUsageEvent.id).label("total_alerts"),
            func.coalesce(func.sum(case((SystemUsageEvent.user_feedback_result == "false_alarm", 1), else_=0)), 0).label("false_alarms_user"),
            func.coalesce(func.sum(case((SystemUsageEvent.auto_verify_result == "false_alarm", 1), else_=0)), 0).label("false_alarms_auto"),
            func.coalesce(func.sum(case(((SystemUsageEvent.user_feedback_result == "false_alarm") | (SystemUsageEvent.auto_verify_result == "false_alarm"), 1), else_=0)), 0).label("false_alarms_total"),
        ).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False,
            SystemUsageEvent.event_category == "proactive_alert"
        )
        summary_res = await session.execute(stmt_summary)
        row = summary_res.one()
        total_alerts = int(row.total_alerts or 0)
        false_alarms_user = int(row.false_alarms_user or 0)
        false_alarms_auto = int(row.false_alarms_auto or 0)
        false_alarms_total = int(row.false_alarms_total or 0)
        true_alarms = total_alerts - false_alarms_total
        false_alarm_rate_pct = round((false_alarms_total / total_alerts) * 100.0, 1) if total_alerts > 0 else 0.0

        # Fetch all proactive alerts in the year to group by month cleanly (database-engine agnostic)
        stmt_events = select(
            SystemUsageEvent.alerted_at,
            SystemUsageEvent.user_feedback_result,
            SystemUsageEvent.auto_verify_result
        ).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False,
            SystemUsageEvent.event_category == "proactive_alert"
        )
        events_res = await session.execute(stmt_events)
        
        # Initialize 12 months dictionary: "YYYY-01" to "YYYY-12"
        monthly_map = {
            f"{target_year}-{m:02d}": {"total": 0, "false_alarm": 0, "true_alarm": 0}
            for m in range(1, 13)
        }

        for ev in events_res.all():
            if ev.alerted_at:
                month_key = ev.alerted_at.strftime("%Y-%m")
                if month_key in monthly_map:
                    is_fa = (ev.user_feedback_result == "false_alarm") or (ev.auto_verify_result == "false_alarm")
                    monthly_map[month_key]["total"] += 1
                    if is_fa:
                        monthly_map[month_key]["false_alarm"] += 1
                    else:
                        monthly_map[month_key]["true_alarm"] += 1

        monthly_breakdown = [
            {
                "month": m_key,
                "total": monthly_map[m_key]["total"],
                "true_alarm": monthly_map[m_key]["true_alarm"],
                "false_alarm": monthly_map[m_key]["false_alarm"],
            }
            for m_key in sorted(monthly_map.keys())
        ]

        return {
            "year": target_year,
            "total_alerts": total_alerts,
            "true_alarms": true_alarms,
            "false_alarms_total": false_alarms_total,
            "false_alarms_user": false_alarms_user,
            "false_alarms_auto": false_alarms_auto,
            "false_alarm_rate_pct": false_alarm_rate_pct,
            "monthly_breakdown": monthly_breakdown
        }


@router.get("/cost")
async def get_monthly_cost(month: Optional[str] = None):
    """
    Monthly Infrastructure & Unit Economics Cost (Issue #292, #293):
    GCP + External Costs, Cost per Alert, Cost per True Alert.
    """
    from app.database import AsyncSessionLocal
    from app.models import ExternalCostConfig, SystemUsageEvent
    from sqlalchemy.future import select
    from sqlalchemy import func, case, distinct

    target_month, start_date, end_date = _get_month_date_range(month)

    # 1. Fetch GCP cost for the requested target_month
    gcp_svc = GCPBillingService()
    try:
        gcp_breakdown = await gcp_svc.get_costs_with_archive(period=target_month)
        gcp_cost_thb = float(gcp_breakdown.total_thb)
    except Exception:
        gcp_cost_thb = 0.0

    # 2. Fetch external costs
    async with AsyncSessionLocal() as session:
        stmt = select(ExternalCostConfig).where(ExternalCostConfig.month == target_month)
        res = await session.execute(stmt)
        ext_configs = res.scalars().all()
        external_cost_thb = float(sum(c.amount_thb for c in ext_configs)) if ext_configs else 0.0

        total_cost_thb = round(gcp_cost_thb + external_cost_thb, 2)

        # 3. Calculate Unit Economics via SQL Aggregation
        stmt_agg = select(
            func.coalesce(func.sum(case((SystemUsageEvent.event_category == "proactive_alert", 1), else_=0)), 0).label("proactive_count"),
            func.coalesce(func.sum(case((SystemUsageEvent.event_category == "ondemand_query", 1), else_=0)), 0).label("ondemand_count"),
            func.count(distinct(SystemUsageEvent.chat_id)).label("unique_users")
        ).where(
            SystemUsageEvent.alerted_at >= start_date,
            SystemUsageEvent.alerted_at < end_date,
            SystemUsageEvent.is_mock == False
        )
        agg_res = await session.execute(stmt_agg)
        agg_row = agg_res.one()

        proactive_count = int(agg_row.proactive_count or 0)
        ondemand_count = int(agg_row.ondemand_count or 0)
        unique_users = int(agg_row.unique_users or 0)
        total_system_usage = proactive_count + ondemand_count

        cost_per_proactive_alert = 0.0
        cost_per_ondemand_query = 0.0
        
        if total_system_usage > 0:
            cost_per_proactive_alert = round((total_cost_thb * (proactive_count / total_system_usage)) / proactive_count, 2) if proactive_count > 0 else 0.0
            cost_per_ondemand_query = round((total_cost_thb * (ondemand_count / total_system_usage)) / ondemand_count, 2) if ondemand_count > 0 else 0.0

        blended_cost_per_active_user = round(total_cost_thb / unique_users, 2) if unique_users > 0 else 0.0

        # Preserve legacy fields for backward compatibility if needed by older dashboards
        cost_per_alert = round(total_cost_thb / total_system_usage, 2) if total_system_usage > 0 else 0.0

        # 4. Generate daily cost breakdown for the month
        import calendar
        y_int, m_int = int(target_month.split("-")[0]), int(target_month.split("-")[1])
        num_days = calendar.monthrange(y_int, m_int)[1]

        daily_gcp = round(gcp_cost_thb / num_days, 2) if num_days > 0 else 0.0
        daily_ext = round(external_cost_thb / num_days, 2) if num_days > 0 else 0.0
        daily_tot = round(daily_gcp + daily_ext, 2)

        daily_cost_breakdown = [
            {
                "date": f"{target_month}-{d:02d}",
                "gcp_cost_thb": daily_gcp,
                "external_cost_thb": daily_ext,
                "total_cost_thb": daily_tot
            }
            for d in range(1, num_days + 1)
        ]

        return {
            "month": target_month,
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
            "mau_count": unique_users,
            "daily_cost_breakdown": daily_cost_breakdown
        }


@router.get("/cost/yearly")
async def get_yearly_cost(year: Optional[str] = None):
    """
    Yearly Cost Metrics:
    Returns 12-month breakdown of external and estimated costs for the specified year ('YYYY').
    """
    from app.database import AsyncSessionLocal
    from app.models import ExternalCostConfig

    target_year, start_date, end_date = _get_year_date_range(year)

    # 1. Fetch GCP costs for each month of the year with DB archiving & caching
    gcp_svc = GCPBillingService()

    import datetime
    now_month = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")

    # Initialize 12 months map
    monthly_costs = {
        f"{target_year}-{m:02d}": {
            "month": f"{target_year}-{m:02d}",
            "external_cost_thb": 0.0,
            "gcp_cost_thb": 0.0,
            "total_cost_thb": 0.0
        }
        for m in range(1, 13)
    }

    # Fetch GCP costs for months up to current month (or all months if past year)
    for m_key in monthly_costs.keys():
        if m_key <= now_month:
            try:
                gcp_res = await gcp_svc.get_costs_with_archive(period=m_key)
                monthly_costs[m_key]["gcp_cost_thb"] = float(gcp_res.total_thb)
            except Exception:
                monthly_costs[m_key]["gcp_cost_thb"] = 0.0

    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select
        # Select all external configs matching target_year-%
        stmt = select(ExternalCostConfig).where(ExternalCostConfig.month.like(f"{target_year}-%"))
        res = await session.execute(stmt)
        configs = res.scalars().all()

        for c in configs:
            if c.month in monthly_costs:
                monthly_costs[c.month]["external_cost_thb"] += float(c.amount_thb)

    for m_key, data in monthly_costs.items():
        data["external_cost_thb"] = round(data["external_cost_thb"], 2)
        data["total_cost_thb"] = round(data["gcp_cost_thb"] + data["external_cost_thb"], 2)


    breakdown_list = [monthly_costs[k] for k in sorted(monthly_costs.keys())]
    total_year_cost = round(sum(item["total_cost_thb"] for item in breakdown_list), 2)

    return {
        "year": target_year,
        "total_cost_thb": total_year_cost,
        "monthly_cost_breakdown": breakdown_list
    }


