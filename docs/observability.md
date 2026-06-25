# Observability & Metrics Guide

This document outlines the procedures for monitoring the health, performance, and queue depths of the FonMaYang system. We utilize Google Cloud native tools combined with external heartbeat monitoring to ensure high availability.

## 1. External Uptime Monitoring (UptimeRobot / BetterStack)

To ensure the core API remains responsive, we expose a lightweight `/health` endpoint. This endpoint does not require authentication and returns a simple JSON status.

**Configuration Steps:**
1. Log in to your UptimeRobot or BetterStack dashboard.
2. Create a new **HTTP(s) Monitor**.
3. Set the URL to your deployed Cloud Run service URL plus `/health` (e.g., `https://fonmayang-api-xyz.a.run.app/health`).
4. Set the monitoring interval (e.g., every 1 minute or 5 minutes).
5. Set the expected HTTP Status Code to `200`.
6. Configure the alert contacts (e.g., Email, SMS, or Telegram) to notify the team if the endpoint goes down.

## 2. Cloud Tasks Queue Monitoring

We use Google Cloud Tasks for background webhook processing and scheduling. To prevent backlogs, we expose the queue depth metric securely.

**Endpoint:** `GET /api/v1/metrics/queue`
- **Header Required:** `X-Cron-Secret` (must match the server's `CRON_SECRET`).
- **Response:**
  ```json
  {
    "queue_name": "webhook-worker-queue",
    "location": "asia-southeast1",
    "depth": 5,
    "status": "success",
    "query_duration_ms": 120,
    "timestamp": 1719320000
  }
  ```

## 3. GCP Performance & Memory Verification Checklist

When deploying new versions (especially those containing caching or performance optimizations like in #71) or investigating incidents, use the following checklist in the Google Cloud Console:

- [ ] **Cloud Run Revisions:** Go to Cloud Run -> Service -> Metrics.
  - [ ] Check **Container Instance Count**: Ensure instances scale up and down correctly. Are there idle instances lingering?
  - [ ] Check **Container Memory Utilization**: Ensure it remains below 80% to avoid Out-Of-Memory (OOM) errors during heavy image processing. Monitor for steady memory growth over time which could indicate memory leaks in the event loop or in-memory caches.
  - [ ] Check **Container CPU Utilization**: Monitor for CPU spikes that correlate with image OCR or prediction tasks.
  - [ ] Check **Request Latency (p50 & p99)**: Verify that latencies meet optimization targets. For instance, post-optimization target for p50 latency is typically `< 5s` (reduced from ~34s).
  - [ ] Check **Billable Container Instance Time**: Ensure container starts and active durations correlate with expected scheduling rates.
- [ ] **Cloud Run Network Metrics:**
  - [ ] Check **Network Ingress**: Verify that bandwidth usage matches the caching implementation. Ingress should be flat and only spike during cache misses or new data fetches (e.g., downloading loop GIFs once per cron instead of per user request).
- [ ] **Cloud Run Logs:** Go to the Logs tab.
  - [ ] Search for `severity >= ERROR` to identify crashes or failed API requests.
- [ ] **Cloud Tasks Dashboard:** Go to Cloud Tasks.
  - [ ] Check **Tasks in Queue**: A high number indicates workers are failing or not keeping up with the dispatch rate.
  - [ ] Check **Retry Rates**: Frequent retries indicate transient errors in the webhook receiver.


## 4. Cloud Scheduler Synchronization (Infra Automation)

To prevent configuration drift between our Infrastructure as Code and the live GCP Console, Cloud Scheduler jobs are managed via a JSON configuration file.

### Editing a Schedule
1. DO NOT edit jobs manually via the GCP Web Console.
2. Edit `backend/config/schedulers.json` locally.
3. Commit and push the changes.
4. The CI/CD pipeline will automatically run `backend/scripts/setup_schedulers.sh` to apply the updates during deployment.

### Recovering from Manual UI Changes
If someone accidentally modified a job schedule via the GCP Web Console (e.g. during an incident), you **must** sync the changes back into the repository to ensure they aren't overwritten on the next deployment:
1. Run the synchronization script:
   ```bash
   python3 backend/scripts/sync_schedulers.py
   ```
2. The script will fetch the live configuration and overwrite `backend/config/schedulers.json`.
3. Commit the updated JSON file to version control.
