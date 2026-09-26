# ADR 013: GCP Cloud Billing In-Memory Caching & PostgreSQL Historical Archiving

## Status
Accepted

## Context
FonMaYang provides public financial transparency and internal unit economics dashboards displaying GCP infrastructure costs (Cloud Run, Cloud Storage, Network Egress, Other).
Currently, the billing service queries Google BigQuery on every API call:
- BigQuery charges for query compute/scan volume on every run.
- Loading the dashboard takes seconds due to BigQuery latency.
- Past months' billing data is static once finalized, yet was being repeatedly queried.
- `/cost` and `/cost/yearly` endpoints had a defect where `period="current_month"` was hardcoded regardless of the requested historical month.

## Decision
We implement a hybrid two-tier caching architecture (Read-through + Auto-Freeze and Scheduled Sync):

1. **In-Memory Cache (Short-term / Hot Path):**
   - For `current_month`, `30d`, and `7d`, cache results in an in-memory TTL cache (e.g. 15 minutes default, or configurable) with support for an explicit bypass/force-refresh parameter.
   - Both summary totals and service/SKU tooltip details are cached together in the same payload for UI consistency.

2. **Persistent Database Archive (Long-term / Cold Path):**
   - A new PostgreSQL model `GcpBillingHistory` (`gcp_billing_history` table) stores finalized billing numbers (`month`, `cloud_run_thb`, `cloud_storage_thb`, `egress_thb`, `other_thb`, `total_thb`, `currency`, and `service_details_json`).
   - **Read-Through Auto-Freeze:** When requesting a historical month (`YYYY-MM`), check the database first. If present, return immediately (0 BigQuery cost, ~0ms latency). If missing, query BigQuery once; if the requested month is a past month and current date > 5th of the current month (ensuring GCP invoice finalization), automatically persist to DB.
   - **Scheduled Sync (Cloud Scheduler Routine):** Add `sync_gcp_billing_history_routine()` running on the 6th of each month to proactively freeze the previous month's bill.

3. **Direct Month Specification (`YYYY-MM`):**
   - Update `GCPBillingService` to accept direct `YYYY-MM` strings in addition to relative periods (`current_month`, `last_month`).
   - Fix `/api/v1/metrics/cost` and `/api/v1/metrics/cost/yearly` to pass through the requested `month` instead of hardcoding `current_month`.

## Consequences
- **Positive:** Drastically reduces BigQuery scan costs to virtually zero for all historical reports and limits active-month queries to cache windows.
- **Positive:** Sub-second response times on dashboard and yearly cost breakdowns.
- **Positive:** Reconciles past records accurately with GCP invoices.
