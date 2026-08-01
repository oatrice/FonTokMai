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
from dataclasses import dataclass
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

    # Deprecated backward compatibility properties if needed
    @property
    def cloud_run_usd(self) -> float:
        return self.cloud_run_thb

    @property
    def cloud_storage_usd(self) -> float:
        return self.cloud_storage_thb

    @property
    def egress_usd(self) -> float:
        return self.egress_thb

    @property
    def other_usd(self) -> float:
        return self.other_thb

    @property
    def total_usd(self) -> float:
        return self.total_thb


class GCPBillingService:
    """Fetches GCP billing data with transparent mock fallback."""

    # Keyword matchers for service categorisation (case-insensitive)
    CLOUD_RUN_KEYWORDS = ["cloud run", "cloud functions"]
    STORAGE_KEYWORDS = ["cloud storage", "gcs"]
    EGRESS_KEYWORDS = ["networking", "egress", "internet egress"]

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.billing_dataset = os.getenv("GCP_BILLING_BIGQUERY_DATASET", "")

    # ─── Mock Data ───────────────────────────────────────────────────────────

    def get_mock_breakdown(self) -> GCPCostBreakdown:
        """Return realistic mock data for dev/staging environments."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return GCPCostBreakdown(
            cloud_run_thb=294.00,
            cloud_storage_thb=42.00,
            egress_thb=21.00,
            other_thb=28.00,
            total_thb=385.00,
            period_start=f"{now.year}-{now.month:02d}-01",
            period_end=now.strftime("%Y-%m-%d"),
            currency="THB",
            is_mock=True,
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

    # ─── Real API Query ──────────────────────────────────────────────────────

    def _query_billing_api(self) -> List[Dict[str, Any]]:
        """Query GCP BigQuery billing export for current month costs.

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

        now = datetime.datetime.now(datetime.timezone.utc)
        period_start = f"{now.year}-{now.month:02d}-01"

        # Supports both 'project.dataset' and 'dataset' formats
        dataset = self.billing_dataset
        query = f"""
            SELECT
                service.description AS service_description,
                SUM(cost) AS cost
            FROM `{dataset}.gcp_billing_export_v1_*`
            WHERE DATE(usage_start_time) >= '{period_start}'
            GROUP BY service.description
            ORDER BY cost DESC
        """
        results = client.query(query).result()
        return [
            {"service_description": row.service_description, "cost": float(row.cost)}
            for row in results
        ]

    # ─── Public Interface ────────────────────────────────────────────────────

    def get_current_month_costs(self) -> GCPCostBreakdown:
        """Fetch current month GCP costs with automatic mock fallback.

        Falls back to mock when:
        - GCP_PROJECT_ID or GCP_BILLING_BIGQUERY_DATASET are not set
        - Google Cloud API call fails (auth error, network issue, etc.)
        """
        if not self.project_id or not self.billing_dataset:
            logger.info("[GCP_BILLING] No project/dataset configured — returning mock data")
            return self.get_mock_breakdown()

        try:
            rows = self._query_billing_api()
            aggregated = self._aggregate_by_service(rows)

            now = datetime.datetime.now(datetime.timezone.utc)
            return GCPCostBreakdown(
                **aggregated,
                total_thb=round(sum(aggregated.values()), 2),
                period_start=f"{now.year}-{now.month:02d}-01",
                period_end=now.strftime("%Y-%m-%d"),
                currency="THB",
                is_mock=False,
            )
        except Exception as e:
            logger.error(f"[GCP_BILLING] API error, falling back to mock: {e}")
            return self.get_mock_breakdown()
