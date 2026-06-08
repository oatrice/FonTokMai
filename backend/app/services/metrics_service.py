import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import LocationRepository

logger = logging.getLogger(__name__)

class MetricsService:
    """Service สำหรับรวบรวมและวิเคราะห์ Metrics ของระบบแบบ In-process"""
    
    def __init__(self, repo: LocationRepository):
        self.repo = repo
        
    async def record_cron_run(
        self,
        routine_name: str,
        duration_s: float,
        alerts_sent: int = 0,
        locations_checked: int = 0,
        errors: int = 0,
        extra_data: Optional[dict] = None
    ):
        """บันทึก telemetry ของ cron routine ลง Repository (Firestore/SQLite)"""
        try:
            now = datetime.now(timezone.utc)
            await self.repo.record_cron_run(
                routine_name=routine_name,
                run_at=now,
                duration_s=duration_s,
                alerts_sent=alerts_sent,
                locations_checked=locations_checked,
                errors=errors,
                extra_data=extra_data
            )
        except Exception as e:
            # Failure to record metrics should not crash the main process
            logger.error(f"Failed to record cron metrics for {routine_name}: {e}")

    async def get_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """ดึงข้อมูล metrics และทำ aggregation สำหรับส่งออกเป็น JSON"""
        try:
            logs = await self.repo.get_cron_metrics(days=days)
        except Exception as e:
            logger.error(f"Failed to fetch cron metrics: {e}")
            logs = []
            
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "routines": {}
        }
        
        for log in logs:
            name = log.get("routine_name", "unknown")
            if name not in summary["routines"]:
                summary["routines"][name] = {
                    "total_runs": 0,
                    "total_alerts_sent": 0,
                    "total_locations_checked": 0,
                    "total_errors": 0,
                    "total_duration_s": 0.0,
                    "avg_duration_s": 0.0,
                    "min_duration_s": float('inf'),
                    "max_duration_s": float('-inf'),
                }
                
            st = summary["routines"][name]
            st["total_runs"] += 1
            st["total_alerts_sent"] += log.get("alerts_sent", 0)
            
            # Since locations_checked might be the same across runs, 
            # this is just a sum of checks performed, not unique locations
            st["total_locations_checked"] += log.get("locations_checked", 0)
            st["total_errors"] += log.get("errors", 0)
            
            dur = log.get("duration_s", 0.0)
            st["total_duration_s"] += dur
            
            if dur < st["min_duration_s"]:
                st["min_duration_s"] = dur
            if dur > st["max_duration_s"]:
                st["max_duration_s"] = dur

        # Calculate averages and cleanup inf
        for name, st in summary["routines"].items():
            runs = st["total_runs"]
            if runs > 0:
                st["avg_duration_s"] = st["total_duration_s"] / runs
            if st["min_duration_s"] == float('inf'):
                st["min_duration_s"] = 0.0
            if st["max_duration_s"] == float('-inf'):
                st["max_duration_s"] = 0.0
                
        return summary
