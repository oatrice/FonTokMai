# Issue 76 & 77: Security & Infrastructure Automation

This document outlines the plans executed to harden the Cloud Run infrastructure security and automate the Cloud Scheduler job migrations.

## 1. Create Dedicated Runtime Service Account for Cloud Run (Issue 76)

Based on the GCP Recommender insight, the `fontokmai-api` Cloud Run service was using the Default Compute Engine Service Account, which has broad permissions (Editor role). This poses a security risk.

We created a dedicated Service Account with minimal privileges required for the application to function securely:
- **Create Service Account**: `cloud-run-runtime`
- **Assign Roles**:
   - `roles/datastore.user` (Firestore Database Access)
   - `roles/cloudtasks.enqueuer` (Google Cloud Tasks queue integration)
   - `roles/storage.objectAdmin` (Firebase Storage bucket access for images)
   - `roles/logging.logWriter` (Cloud Logging for application logs)
   - `roles/monitoring.metricWriter` (Cloud Monitoring metrics)
   - `roles/cloudtrace.agent` (Cloud Trace)

We updated the `gcloud run deploy` command in `.gitlab-ci.yml` to use this Service Account.

## 2. Automate Cloud Scheduler Jobs Migration (Issue 77)

Since we migrated the Cloud Run service to `asia-southeast1`, the existing Cloud Scheduler jobs in `us-central1` would no longer work. Furthermore, manually configuring Scheduler jobs is error-prone.

We created an automation script `backend/scripts/setup_schedulers.sh` that:
1. Detects the current `fontokmai-api` Cloud Run URL automatically.
2. Checks for the `CRON_SECRET` variable to inject into the `X-Cron-Secret` header for security.
3. Loops through our required endpoints (`check-rain`, `check-disasters-frequent`, `check-disasters-infrequent`, `fetch-tmd-radar`) and creates/updates the Google Cloud Scheduler jobs in `asia-southeast1`.
4. Deletes the old `fonmayang-rain-check` job in `us-central1` to clean up.

## 3. Automate Cloud Scheduler Deployment in CI/CD (Issue 77)

Relying on humans to manually run `setup_schedulers.sh` is risky and can lead to broken background jobs if forgotten. 

We integrated the script directly into our GitLab CI/CD pipeline (`.gitlab-ci.yml`). This ensures that every time we merge to the `main` branch, the CI/CD pipeline will automatically set up and update the Cloud Scheduler jobs immediately after the Cloud Run deployment finishes.
