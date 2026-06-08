import os
import io
import csv
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, Response

from app.dependencies import get_repo_context
from app.services.metrics_service import MetricsService

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["metrics"]
)

CRON_SECRET = os.getenv("CRON_SECRET", "default_secret_for_local_testing")

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
    if not x_cron_secret or x_cron_secret != CRON_SECRET:
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
                    import json
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
