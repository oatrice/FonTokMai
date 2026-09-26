"""
GCPBillingService — Fetch monthly GCP infrastructure costs (Issue #211).

Queries GCP Cloud Billing data via BigQuery export dataset.
Gracefully falls back to mock data when credentials/config are unavailable,
ensuring the dashboard always renders something useful.

Service breakdown categories:
  - Cloud Run (compute)
  - Cloud Storage (storage)
  - Network Egress (bandwidth)
  - Other (everything else)
"""
import os
import json
import asyncio
import logging
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import SystemConfig, GcpBillingHistory

logger = logging.getLogger(__name__)

# Invoice is considered finalized after the 5th day of the following month
INVOICE_FINALIZATION_DAY: int = 6


@dataclass
class GCPCostBreakdown:
    """Immutable cost breakdown for one billing period."""
    cloud_run_thb: float = 0.0
    cloud_storage_thb: float = 0.0
    egress_thb: float = 0.0
    other_thb: float = 0.0
    total_thb: float = 0.0
    period_start: str = ""
    period_end: str = ""
    currency: str = "THB"
    is_mock: bool = True
    service_details: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Informational USD approximation (billing account is THB, ~35 THB/USD)
    @property
    def cloud_run_usd(self) -> float:
        return round(self.cloud_run_thb / 35.0, 2)

    @property
    def cloud_storage_usd(self) -> float:
        return round(self.cloud_storage_thb / 35.0, 2)

    @property
    def egress_usd(self) -> float:
        return round(self.egress_thb / 35.0, 2)

    @property
    def other_usd(self) -> float:
        return round(self.other_thb / 35.0, 2)

    @property
    def total_usd(self) -> float:
        return round(self.total_thb / 35.0, 2)


class GCPBillingService:
    """Fetches GCP billing data with transparent mock fallback."""

    # Keyword matchers for service categorisation (case-insensitive)
    CLOUD_RUN_KEYWORDS = ["cloud run", "cloud functions"]
    STORAGE_KEYWORDS = ["cloud storage", "gcs"]
    EGRESS_KEYWORDS = ["networking", "egress", "internet egress"]

    # In-memory cache: (period, require_real_data) -> (GCPCostBreakdown, timestamp)
    _CACHE: Dict[str, tuple[GCPCostBreakdown, float]] = {}
    DEFAULT_CACHE_TTL_SECONDS: float = 900.0  # 15 minutes default

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory billing cache."""
        cls._CACHE.clear()

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.billing_dataset = os.getenv("GCP_BILLING_BIGQUERY_DATASET", "")
        self.billing_project_filter = os.getenv("GCP_BILLING_PROJECT_FILTER", self.project_id)
        # Configurable TTL via env
        self.cache_ttl = float(os.getenv("GCP_BILLING_CACHE_TTL", str(self.DEFAULT_CACHE_TTL_SECONDS)))

    def _bool_env(self, key: str, default: bool = False) -> bool:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _default_force_real_data(self) -> bool:
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        return env_name in {"staging", "production", "prod", "main"}

    def should_force_real_data(self) -> bool:
        """Resolve the sync-safe default policy for callers that cannot await.

        Used by direct service calls and tests. Async request handlers should use
        `resolve_force_real_data()` when they need Neon-first precedence.
        """
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        default = self._default_force_real_data()

        # Sync callers cannot consult Neon, so local/dev only gets an explicit
        # "true" override here. "false"/unset means "defer to async policy".
        explicit = os.getenv("FORCE_GCP_REAL_DATA")
        if env_name in {"development", "dev", "local", "test"} and explicit is not None:
            if explicit.strip().lower() in {"1", "true", "yes", "on"}:
                logger.info(
                    "[GCP_BILLING] Policy resolved from env override for %s: FORCE_GCP_REAL_DATA=%s resolved=true",
                    env_name,
                    explicit,
                )
                return True

        logger.info(
            "[GCP_BILLING] Policy deferred to async/default for %s: FORCE_GCP_REAL_DATA=%s default=%s",
            env_name,
            os.getenv("FORCE_GCP_REAL_DATA", ""),
            default,
        )
        return default

    async def resolve_force_real_data(self) -> bool:
        """Resolve real-data policy using the single-source-of-truth matrix.

        Precedence:
          1. local/dev: explicit FORCE_GCP_REAL_DATA env override, then default false
          2. staging/prod: Neon `system_config.gcp_force_real_data` first
          3. fallback: environment default when DB is unavailable or key is missing
        """
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        is_local_debug = env_name in {"development", "dev", "local", "test"}
        default = self._default_force_real_data()

        if is_local_debug:
            explicit = os.getenv("FORCE_GCP_REAL_DATA")
            if explicit is not None and explicit.strip().lower() in {"1", "true", "yes", "on"}:
                logger.info(
                    "[GCP_BILLING] resolve_force_real_data(local) env=%s FORCE_GCP_REAL_DATA=%s resolved=true",
                    env_name,
                    explicit,
                )
                return True
            logger.info(
                "[GCP_BILLING] resolve_force_real_data(local) env=%s FORCE_GCP_REAL_DATA=%s default=%s -> checking Neon/default path",
                env_name,
                os.getenv("FORCE_GCP_REAL_DATA", ""),
                default,
            )

        db_url = os.getenv("DATABASE_URL", "")
        logger.info(
            "[GCP_BILLING] resolve_force_real_data(non-local) env=%s default=%s db_present=%s",
            env_name,
            default,
            bool(db_url),
        )
        if db_url.startswith("postgres://") or db_url.startswith("postgresql://") or "postgresql+asyncpg://" in db_url:
            try:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(SystemConfig.value_json).where(SystemConfig.key == "gcp_force_real_data")
                    )
                    raw_value = res.scalar_one_or_none()
                    if raw_value is not None:
                        resolved = str(raw_value).strip().lower() in {"1", "true", "yes", "on"}
                        logger.info(
                            "[GCP_BILLING] Neon override resolved env=%s raw=%s resolved=%s",
                            env_name,
                            raw_value,
                            resolved,
                        )
                        return resolved
            except Exception as e:
                logger.warning("[GCP_BILLING] Neon override unavailable, using default: %s", e)

        logger.info(
            "[GCP_BILLING] Neon override missing/unavailable, falling back to default=%s for env=%s",
            default,
            env_name,
        )
        return default

    def _get_date_range(self, period: str) -> tuple[str, str]:
        """Calculate period_start and period_end YYYY-MM-DD for a given period or explicit 'YYYY-MM'."""
        import calendar
        now = datetime.datetime.now(datetime.timezone.utc).date()
        if period == "last_month":
            first_of_this_month = now.replace(day=1)
            last_day_of_last_month = first_of_this_month - datetime.timedelta(days=1)
            first_day_of_last_month = last_day_of_last_month.replace(day=1)
            return first_day_of_last_month.strftime("%Y-%m-%d"), last_day_of_last_month.strftime("%Y-%m-%d")
        elif period == "30d":
            start_date = now - datetime.timedelta(days=30)
            return start_date.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
        elif period == "7d":
            start_date = now - datetime.timedelta(days=7)
            return start_date.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
        elif len(period) == 7 and period[4] == "-":
            try:
                y, m = int(period[:4]), int(period[5:7])
                _, last_day = calendar.monthrange(y, m)
                return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last_day:02d}"
            except Exception:
                pass
        # Default: current_month
        start_date = now.replace(day=1)
        return start_date.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")


    # ─── Mock Data ───────────────────────────────────────────────────────────

    def get_mock_breakdown(self, period: str = "current_month") -> GCPCostBreakdown:
        """Return realistic mock data for dev/staging environments."""
        period_start, period_end = self._get_date_range(period)
        
        # Scale mock numbers slightly based on period
        multiplier = 1.0
        if period == "last_month":
            multiplier = 1.25
        elif period == "30d":
            multiplier = 1.10
        elif period == "7d":
            multiplier = 0.25

        cloud_run = round(294.00 * multiplier, 2)
        storage = round(42.00 * multiplier, 2)
        egress = round(21.00 * multiplier, 2)
        other = round(28.00 * multiplier, 2)
        total = round(cloud_run + storage + egress + other, 2)

        return GCPCostBreakdown(
            cloud_run_thb=cloud_run,
            cloud_storage_thb=storage,
            egress_thb=egress,
            other_thb=other,
            total_thb=total,
            period_start=period_start,
            period_end=period_end,
            currency="THB",
            is_mock=True,
            service_details={
                "cloud_run_thb": [{"service": "Cloud Run", "sku": "Mock compute", "cost_thb": cloud_run}],
                "cloud_storage_thb": [{"service": "Cloud Storage", "sku": "Mock storage", "cost_thb": storage}],
                "egress_thb": [{"service": "Networking", "sku": "Mock egress", "cost_thb": egress}],
                "other_thb": [{"service": "Other Services", "sku": "Mock other", "cost_thb": other}],
            },
        )

    # ─── Aggregation Logic ───────────────────────────────────────────────────

    def _aggregate_by_service(self, rows: List[Dict[str, Any]]) -> Dict[str, float]:
        """Bucket raw BigQuery billing rows into our 4 service categories."""
        cloud_run = 0.0
        storage = 0.0
        egress = 0.0
        other = 0.0

        for row in rows:
            service = row.get("service_description", "").lower()
            cost = float(row.get("cost", 0.0))

            if any(kw in service for kw in self.CLOUD_RUN_KEYWORDS):
                cloud_run += cost
            elif any(kw in service for kw in self.STORAGE_KEYWORDS):
                storage += cost
            elif any(kw in service for kw in self.EGRESS_KEYWORDS):
                egress += cost
            else:
                other += cost

        return {
            "cloud_run_thb": round(cloud_run, 2),
            "cloud_storage_thb": round(storage, 2),
            "egress_thb": round(egress, 2),
            "other_thb": round(other, 2),
        }

    def _category_for_service(self, service: str) -> str:
        """Map a GCP service name to the dashboard cost bucket."""
        service_lower = service.lower()
        if any(kw in service_lower for kw in self.CLOUD_RUN_KEYWORDS):
            return "cloud_run_thb"
        if any(kw in service_lower for kw in self.STORAGE_KEYWORDS):
            return "cloud_storage_thb"
        if any(kw in service_lower for kw in self.EGRESS_KEYWORDS):
            return "egress_thb"
        return "other_thb"

    def _build_service_details(self, rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Expose the raw service/SKU rows used by each dashboard bucket."""
        details: Dict[str, List[Dict[str, Any]]] = {
            "cloud_run_thb": [],
            "cloud_storage_thb": [],
            "egress_thb": [],
            "other_thb": [],
        }

        for row in rows:
            service = row.get("service_description", "")
            category = self._category_for_service(service)
            cost = round(float(row.get("cost", 0.0)), 2)
            if cost == 0:
                continue
            details[category].append({
                "project_id": row.get("project_id", ""),
                "service": service,
                "sku": row.get("sku_description", ""),
                "cost_thb": cost,
            })

        for category_rows in details.values():
            category_rows.sort(key=lambda item: abs(item["cost_thb"]), reverse=True)

        return details

    # ─── Real API Query ──────────────────────────────────────────────────────

    def _query_billing_api(self, period: str, period_start: str, period_end: str) -> List[Dict[str, Any]]:
        """Query GCP BigQuery billing export for specified period range or invoice month.

        Requires:
          - GOOGLE_APPLICATION_CREDENTIALS (service account with BigQuery reader)
          - GCP_PROJECT_ID
          - GCP_BILLING_BIGQUERY_DATASET (format: project.dataset or dataset)
        """
        try:
            from google.cloud import bigquery  # type: ignore
        except ImportError as e:
            raise Exception(f"google-cloud-bigquery not installed: {e}") from e

        client = bigquery.Client(project=self.project_id)
        dataset = self.billing_dataset

        # Match the dashboard period label and GCP Console Reports date-range view.
        where_clause = f"DATE(usage_start_time) BETWEEN '{period_start}' AND '{period_end}'"

        project_filter = self.billing_project_filter.strip()
        if project_filter and project_filter.lower() != "all":
            safe_project_filter = project_filter.replace("'", "''")
            where_clause += f" AND project.id = '{safe_project_filter}'"

        query = f"""
            SELECT
                project.id AS project_id,
                service.description AS service_description,
                sku.description AS sku_description,
                SUM(cost + COALESCE((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) AS cost
            FROM `{dataset}.gcp_billing_export_v1_*`
            WHERE {where_clause}
            GROUP BY project.id, service.description, sku.description
            ORDER BY cost DESC
        """
        results = client.query(query).result()
        return [
            {
                "project_id": row.project_id,
                "service_description": row.service_description,
                "sku_description": row.sku_description,
                "cost": float(row.cost),
            }
            for row in results
        ]

    # ─── Public Interface ────────────────────────────────────────────────────

    def get_current_month_costs(
        self,
        period: str = "current_month",
        require_real_data: bool | None = None,
        force_refresh: bool = False,
    ) -> GCPCostBreakdown:
        """Fetch GCP costs for given period with automatic mock fallback and in-memory cache.

        Falls back to mock when:
        - GCP_PROJECT_ID or GCP_BILLING_BIGQUERY_DATASET are not set
        - Google Cloud API call fails (auth error, network issue, etc.)
        """
        import time

        if require_real_data is None:
            require_real_data = self.should_force_real_data()

        cache_key = f"{period}:{require_real_data}"
        now_ts = time.time()

        if not force_refresh and cache_key in self._CACHE:
            cached_data, cached_ts = self._CACHE[cache_key]
            if now_ts - cached_ts < self.cache_ttl:
                logger.info("[GCP_BILLING] Cache hit for %s (age=%.1fs)", cache_key, now_ts - cached_ts)
                return cached_data

        logger.info(
            "[GCP_BILLING] get_current_month_costs period=%s require_real_data=%s force_refresh=%s project_id_present=%s dataset_present=%s",
            period,
            require_real_data,
            force_refresh,
            bool(self.project_id),
            bool(self.billing_dataset),
        )

        if not require_real_data:
            logger.info("[GCP_BILLING] Mock-only mode enabled; returning mock data without querying BigQuery")
            breakdown = self.get_mock_breakdown(period=period)
            self._CACHE[cache_key] = (breakdown, now_ts)
            return breakdown

        if not self.project_id or not self.billing_dataset:
            logger.warning("[GCP_BILLING] Missing config and real-data mode enabled; raising instead of mock fallback")
            raise RuntimeError(
                "GCP billing config is missing; "
                "set GCP_PROJECT_ID and GCP_BILLING_BIGQUERY_DATASET to enable real burn-rate sync."
            )

        period_start, period_end = self._get_date_range(period)

        try:
            # BigQuery Billing Export already returns costs in THB
            # (GCP billing account currency is THB — no conversion needed)
            rows = self._query_billing_api(period=period, period_start=period_start, period_end=period_end)
            logger.info("[GCP_BILLING] BigQuery query returned %d rows", len(rows))
            aggregated_thb = self._aggregate_by_service(rows)
            service_details = self._build_service_details(rows)

            breakdown = GCPCostBreakdown(
                **aggregated_thb,
                total_thb=round(sum(aggregated_thb.values()), 2),
                period_start=period_start,
                period_end=period_end,
                currency="THB",
                is_mock=False,
                service_details=service_details,
            )
            self._CACHE[cache_key] = (breakdown, now_ts)
            return breakdown
        except Exception as e:
            if require_real_data:
                logger.exception("[GCP_BILLING] Real data requested but fetch failed; raising")
                raise RuntimeError(f"Failed to fetch real GCP billing data: {e}") from e
            logger.error(f"[GCP_BILLING] API error, falling back to mock: {e}")
            breakdown = self.get_mock_breakdown(period=period)
            self._CACHE[cache_key] = (breakdown, now_ts)
            return breakdown

    async def get_costs_with_archive(
        self,
        period: str = "current_month",
        require_real_data: bool | None = None,
        force_refresh: bool = False,
    ) -> GCPCostBreakdown:
        """Fetch GCP costs with Database Archiving (Issue #249, #339).

        1. If requested period is a past month ('YYYY-MM' or 'last_month') and present in DB,
           return directly from PostgreSQL without hitting BigQuery.
        2. Otherwise, fetch via BigQuery/cache (offloaded to a thread via asyncio.to_thread
           to avoid blocking the async event loop during synchronous BigQuery network I/O).
        3. If it's a past month and today >= INVOICE_FINALIZATION_DAY of current month
           (invoice finalized), persist to DB automatically.
        """
        if require_real_data is None:
            require_real_data = await self.resolve_force_real_data()

        # Resolve explicit month string if possible
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        current_month_str = now_dt.strftime("%Y-%m")

        target_month_str = None
        if len(period) == 7 and period[4] == "-":
            target_month_str = period
        elif period == "last_month":
            first_of_this_month = now_dt.date().replace(day=1)
            last_day_of_last_month = first_of_this_month - datetime.timedelta(days=1)
            target_month_str = last_day_of_last_month.strftime("%Y-%m")

        is_past_month = target_month_str is not None and target_month_str < current_month_str

        # Step 1: Check Database Archive if it's a past month and not forced refresh.
        # We also capture 'history_row' to reuse in the can_freeze upsert (avoids double SELECT).
        history_row = None
        if is_past_month and not force_refresh:
            try:
                async with AsyncSessionLocal() as session:
                    stmt = select(GcpBillingHistory).where(GcpBillingHistory.month == target_month_str)
                    res = await session.execute(stmt)
                    history_row = res.scalar_one_or_none()
                    if history_row:
                        logger.info("[GCP_BILLING] Returning archived cost from DB for month=%s", target_month_str)
                        service_details = {}
                        if history_row.service_details_json:
                            try:
                                service_details = json.loads(history_row.service_details_json)
                            except Exception:
                                pass

                        return GCPCostBreakdown(
                            cloud_run_thb=float(history_row.cloud_run_thb),
                            cloud_storage_thb=float(history_row.cloud_storage_thb),
                            egress_thb=float(history_row.egress_thb),
                            other_thb=float(history_row.other_thb),
                            total_thb=float(history_row.total_thb),
                            period_start=history_row.period_start or f"{target_month_str}-01",
                            period_end=history_row.period_end or f"{target_month_str}-28",
                            currency=history_row.currency or "THB",
                            is_mock=False,
                            service_details=service_details,
                        )
            except Exception as e:
                logger.warning("[GCP_BILLING] Failed to query GcpBillingHistory from DB: %s", e)

        # Step 2: Fetch via BigQuery/cache.
        # Offload to a thread pool so the blocking BigQuery network call does not stall the event loop.
        breakdown = await asyncio.to_thread(
            self.get_current_month_costs,
            period,
            require_real_data,
            force_refresh,
        )

        # Step 3: Auto-Freeze / Persist to DB if past month, real data, and past invoice finalization day.
        # If past month is earlier than last month → always finalized.
        # If it is last month → finalized once INVOICE_FINALIZATION_DAY has passed.
        can_freeze = False
        if is_past_month and not breakdown.is_mock:
            first_of_this_month = now_dt.date().replace(day=1)
            last_day_of_last_month = first_of_this_month - datetime.timedelta(days=1)
            last_month_str = last_day_of_last_month.strftime("%Y-%m")

            if target_month_str < last_month_str:
                can_freeze = True
            elif target_month_str == last_month_str and now_dt.day >= INVOICE_FINALIZATION_DAY:
                can_freeze = True

        if can_freeze:
            try:
                async with AsyncSessionLocal() as session:
                    # history_row from Step 1 tells us whether a record already exists.
                    # Re-fetch only when force_refresh=True (history_row was not populated above).
                    existing = history_row
                    if existing is None and force_refresh:
                        stmt = select(GcpBillingHistory).where(GcpBillingHistory.month == target_month_str)
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()

                    details_json = json.dumps(breakdown.service_details) if breakdown.service_details else None
                    now_naive = now_dt.replace(tzinfo=None)

                    if existing:
                        existing.cloud_run_thb = breakdown.cloud_run_thb
                        existing.cloud_storage_thb = breakdown.cloud_storage_thb
                        existing.egress_thb = breakdown.egress_thb
                        existing.other_thb = breakdown.other_thb
                        existing.total_thb = breakdown.total_thb
                        existing.currency = breakdown.currency
                        existing.period_start = breakdown.period_start
                        existing.period_end = breakdown.period_end
                        existing.service_details_json = details_json
                        existing.updated_at = now_naive
                        session.add(existing)
                    else:
                        new_record = GcpBillingHistory(
                            month=target_month_str,
                            cloud_run_thb=breakdown.cloud_run_thb,
                            cloud_storage_thb=breakdown.cloud_storage_thb,
                            egress_thb=breakdown.egress_thb,
                            other_thb=breakdown.other_thb,
                            total_thb=breakdown.total_thb,
                            currency=breakdown.currency,
                            period_start=breakdown.period_start,
                            period_end=breakdown.period_end,
                            service_details_json=details_json,
                            created_at=now_naive,
                            updated_at=now_naive,
                        )
                        session.add(new_record)
                    await session.commit()
                    logger.info("[GCP_BILLING] Archived finalized billing data to DB for month=%s", target_month_str)
            except Exception as e:
                logger.warning("[GCP_BILLING] Failed to auto-freeze billing data to DB: %s", e)

        return breakdown


