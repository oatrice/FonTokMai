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

Runway definition for the dashboard: `Runway is calculated from total cash on hand divided by actual monthly burn only, using expenses already paid; reserved budgets, free-tier usage, and projected future costs are shown separately and are not included in the main runway figure.`

## Runtime Policy

`gcp_force_real_data` follows this precedence:

1. `local` / `dev`: `FORCE_GCP_REAL_DATA=true` forces real data; `false` or unset defers to Neon/default
2. `staging` / `production`: Neon `system_config.gcp_force_real_data` first
3. If Neon is unavailable or the key is missing, fall back to the runtime default for that environment

This keeps local debugging flexible while making staging/prod deterministic and safe when the database is temporarily unavailable.

## Future Consistency Option

If we later want the simplest cross-environment behavior, use this precedence everywhere:

`FORCE_GCP_REAL_DATA` explicit override > Neon `system_config.gcp_force_real_data` > `ENVIRONMENT` default > safe fallback

That version is easier to reason about because every environment follows the same shape. It is not the active policy yet; it is only a recommended future simplification.

## Environment Separation Matrix

Recommended isolation boundaries for `dev` / `staging` / `production`:

| Item | dev | staging | production | Recommendation |
|---|---|---|---|---|
| Billing account | Separate preferred | Separate required | Separate required | Keep prod billing isolated; if dev must share, apply strict budgets and labels. |
| GCP project | Separate | Separate | Separate | Never share a project across environments. |
| BigQuery billing dataset | Separate | Separate | Separate | Keep per-env datasets so burn-rate reads cannot cross environments. |
| Neon DB | Separate DB / branch | Separate DB / branch | Separate DB / branch | Do not share the same writable DB across envs. |
| Backend / worker URL | Separate service URL | Separate service URL | Separate service URL | Each env should point to its own backend and worker endpoints. |
| Secrets / config | Separate values | Separate values | Separate values | Use the same key names, but env-specific secret values and config defaults. |

Practical rule:

- `dev` can be noisy and disposable.
- `staging` should mirror production as closely as possible without sharing production targets.
- `production` must never fall back to a dev/staging worker, DB, or billing dataset.
