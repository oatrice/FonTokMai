### Manual Verification Guide

This guide outlines how to verify the new Google Cloud Scheduler configuration script (`backend/scripts/setup_schedulers.sh`) and its integration into the deployment flow.

---

### Step 1: Pre-requisites & Local Environment Prep
Make sure you are logged in to GCP on your command line and have targeted the correct project.
1. Run `gcloud auth login` and ensure you are authenticated.
2. Set your active project to `fonmayang`:
   ```bash
   gcloud config set project fonmayang
   ```
3. Prepare a local `.env` file in the `backend/` directory or export `CRON_SECRET`:
   ```bash
   export CRON_SECRET="test_secret_123"
   ```

### Step 2: Run the script locally in dry-run/read-only mode
Before creating or updating actual jobs, test the Cloud Run URL lookup by running the first part of the script or reviewing it.
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Check if the Cloud Run URL fetches correctly:
   ```bash
   gcloud run services describe fontokmai-api \
     --platform managed \
     --region asia-southeast1 \
     --project fonmayang \
     --format 'value(status.url)'
   ```

### Step 3: Run the Scheduler Setup Script
1. Run the script manually from the `backend/` directory:
   ```bash
   chmod +x scripts/setup_schedulers.sh
   ./scripts/setup_schedulers.sh
   ```
2. Verify that the output shows the setup progress for all 4 jobs:
   - `fonmayang-check-rain`
   - `fonmayang-disasters-freq`
   - `fonmayang-disasters-infreq`
   - `fonmayang-fetch-radar`

### Step 4: Verify Scheduler Jobs Status on GCP
1. List the scheduler jobs in the region to confirm they exist and are targetting the correct URL and region (`asia-southeast1`):
   ```bash
   gcloud scheduler jobs list --location=asia-southeast1 --project=fonmayang
   ```
2. Check a specific job to verify headers (such as `X-Cron-Secret` containing the correct secret value) and the Bangkok timezone configuration:
   ```bash
   gcloud scheduler jobs describe fonmayang-check-rain --location=asia-southeast1 --project=fonmayang
   ```

### Expected Result
- The script successfully fetches the Cloud Run base URL for `fontokmai-api` in `asia-southeast1`.
- The script correctly identifies the `CRON_SECRET` from the environment or `.env` file.
- The 4 Cloud Scheduler jobs are created or updated in the `asia-southeast1` region.
- `gcloud scheduler jobs describe` shows the HTTP target URLs are correctly prefixing the Cloud Run base URL (e.g. `https://[RUN-URL]/api/v1/scheduler/check-rain`).
- The timezone for all jobs is set to `Asia/Bangkok`.
- The description of the jobs reads: `⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh`.
