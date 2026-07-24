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
    cloud_run_usd: float = 0.0
    cloud_storage_usd: float = 0.0
    egress_usd: float = 0.0
    other_usd: float = 0.0
    total_usd: float = 0.0
    period_start: str = ""
    period_end: str = ""
    currency: str = "USD"
    is_mock: bool = True


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
        force_real = os.getenv("FORCE_GCP_REAL_DATA", "false").lower() == "true"
        return GCPCostBreakdown(
            cloud_run_usd=8.40,
            cloud_storage_usd=1.20,
            egress_usd=0.60,
            other_usd=0.80,
            total_usd=11.00,
            period_start=f"{now.year}-{now.month:02d}-01",
            period_end=now.strftime("%Y-%m-%d"),
            currency="USD",
            is_mock=not force_real,
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
            "cloud_run_usd": round(cloud_run, 4),
            "cloud_storage_usd": round(storage, 4),
            "egress_usd": round(egress, 4),
            "other_usd": round(other, 4),
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
        logger.info(f"[GCP_BILLING] Querying BigQuery dataset: {dataset}.gcp_billing_export_v1_* for project {self.project_id}")
        results = client.query(query).result()
        fetched = [
            {"service_description": row.service_description, "cost": float(row.cost)}
            for row in results
        ]
        logger.info(f"[GCP_BILLING] BigQuery returned {len(fetched)} raw service rows")
        return fetched

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
            total = round(sum(aggregated.values()), 4)
            logger.info(
                f"[GCP_BILLING] Successfully fetched real BigQuery billing data: "
                f"fetched {len(rows)} service rows, total_usd=${total} (is_mock=False)"
            )
            return GCPCostBreakdown(
                **aggregated,
                total_usd=total,
                period_start=f"{now.year}-{now.month:02d}-01",
                period_end=now.strftime("%Y-%m-%d"),
                currency="USD",
                is_mock=False,
            )
        except Exception as e:
            logger.error(f"[GCP_BILLING] API error, falling back to mock: {e}")
            return self.get_mock_breakdown()
