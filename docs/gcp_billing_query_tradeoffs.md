# GCP Billing Query Tradeoffs

Date noted: 2026-08-03

## Context

FonMaYang reads GCP costs from the BigQuery Cloud Billing export for the dashboard and burn-rate sync. The GCP Console Billing Report can generate a more complex SQL query than the dashboard's original query.

Important differences observed:

- Console Billing Report uses `usage_start_time` boundaries in `US/Pacific`.
- Console Billing Report excludes `cost_type = 'tax'` and `cost_type = 'adjustment'`.
- Console Billing Report separates CUD credits, other savings, negotiated savings, and list/effective price fields.
- The dashboard originally used a simpler net-cost formula: `cost + SUM(all credits)`.
- The dashboard now filters by `project.id` through `GCP_BILLING_PROJECT_FILTER`, defaulting to `GCP_PROJECT_ID`, to avoid billing-account-wide totals.
- For explaining Cloud Storage and Other Services, the API should expose service/SKU detail rows, not only bucket totals.

## Tradeoff

Use the Console-compatible query when the dashboard must reconcile exactly with GCP Console Billing Reports.

Use the simpler net-cost query when the dashboard needs a stable operational burn-rate signal and exact Console reconciliation is less important.

## Current Recommendation

For the public financial dashboard, prefer Console-compatible semantics:

- Filter by `project.id`.
- Filter by `usage_start_time` date range.
- Exclude tax and adjustment rows.
- Keep SKU-level details available for tooltips.
- Treat credits/savings consistently with GCP Console if exact visual reconciliation becomes a requirement.

For internal quick diagnostics, the simpler `cost + credits` query remains useful because it is easier to inspect and reason about.
