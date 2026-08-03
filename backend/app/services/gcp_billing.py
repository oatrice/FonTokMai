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
import logging
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.billing_dataset = os.getenv("GCP_BILLING_BIGQUERY_DATASET", "")
        self.billing_project_filter = os.getenv("GCP_BILLING_PROJECT_FILTER", self.project_id)

    def _get_date_range(self, period: str) -> tuple[str, str]:
        """Calculate period_start and period_end YYYY-MM-DD for a given period."""
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
        else:
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

    def get_current_month_costs(self, period: str = "current_month", require_real_data: bool = False) -> GCPCostBreakdown:
        """Fetch GCP costs for given period with automatic mock fallback.

        Falls back to mock when:
        - GCP_PROJECT_ID or GCP_BILLING_BIGQUERY_DATASET are not set
        - Google Cloud API call fails (auth error, network issue, etc.)
        """
        if not self.project_id or not self.billing_dataset:
            if require_real_data:
                raise RuntimeError(
                    "GCP billing config is missing; "
                    "set GCP_PROJECT_ID and GCP_BILLING_BIGQUERY_DATASET to enable real burn-rate sync."
                )
            logger.info("[GCP_BILLING] No project/dataset configured — returning mock data")
            return self.get_mock_breakdown(period=period)

        period_start, period_end = self._get_date_range(period)

        try:
            # BigQuery Billing Export already returns costs in THB
            # (GCP billing account currency is THB — no conversion needed)
            rows = self._query_billing_api(period=period, period_start=period_start, period_end=period_end)
            aggregated_thb = self._aggregate_by_service(rows)
            service_details = self._build_service_details(rows)

            return GCPCostBreakdown(
                **aggregated_thb,
                total_thb=round(sum(aggregated_thb.values()), 2),
                period_start=period_start,
                period_end=period_end,
                currency="THB",
                is_mock=False,
                service_details=service_details,
            )
        except Exception as e:
            if require_real_data:
                raise RuntimeError(f"Failed to fetch real GCP billing data: {e}") from e
            logger.error(f"[GCP_BILLING] API error, falling back to mock: {e}")
            return self.get_mock_breakdown(period=period)
