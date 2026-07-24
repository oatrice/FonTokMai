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
async def get_gcp_costs(x_cron_secret: str = Header(None)):
    """
    Fetch monthly GCP infrastructure costs broken down by service.

    Returns mock data transparently when GCP credentials are not configured.
    Requires x-cron-secret header for authentication.

    Response schema: GCPCostBreakdown dataclass fields:
      cloud_run_usd, cloud_storage_usd, egress_usd, other_usd,
      total_usd, period_start, period_end, currency, is_mock
    """
    server_secret = os.getenv("CRON_SECRET")
    if (
        not server_secret
        or not x_cron_secret
        or not secrets.compare_digest(x_cron_secret, server_secret)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    svc = GCPBillingService()
    breakdown = svc.get_current_month_costs()
    return JSONResponse(content=asdict(breakdown))
