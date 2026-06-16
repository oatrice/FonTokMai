# Walkthrough: Security & Infrastructure Automation

## Changes Made

### 1. Dedicated Service Account for Cloud Run (Issue 76)
Following the GCP Recommender insight to enforce least-privilege security, we created a dedicated Service Account for the `fontokmai-api` Cloud Run service and configured it in the deployment pipeline.
1. **Created Service Account**: `cloud-run-runtime@fonmayang.iam.gserviceaccount.com`
2. **Assigned Minimal IAM Roles**: `roles/datastore.user`, `roles/cloudtasks.enqueuer`, `roles/storage.objectAdmin`, `roles/logging.logWriter`, `roles/monitoring.metricWriter`, `roles/cloudtrace.agent`.
3. **Updated CI Pipeline**: Modified `.gitlab-ci.yml` so the `gcloud run deploy` command sets `--service-account=cloud-run-runtime@fonmayang.iam.gserviceaccount.com`.

### 2. Cloud Scheduler Automation Script (Issue 77)
To address the broken Cloud Scheduler jobs pointing to the old `us-central1` Cloud Run service, we created an automation script to re-deploy them correctly to `asia-southeast1`.
1. **Created Automation Script**: Wrote `backend/scripts/setup_schedulers.sh`.
   - The script automatically fetches the current Cloud Run base URL for `fontokmai-api` in `asia-southeast1`.
   - It pulls the `CRON_SECRET` from the environment or `.env` and injects it into the `X-Cron-Secret` HTTP header for security.
   - It creates/updates the following scheduler jobs with the `⚠️ DO NOT EDIT` warning description:
     - `fonmayang-check-rain` (`*/20 * * * *`)
     - `fonmayang-disasters-freq` (`*/5 * * * *`)
     - `fonmayang-disasters-infreq` (`0 * * * *`)
     - `fonmayang-fetch-radar` (`*/5 * * * *`)
2. **Cleanup**: Executed `gcloud scheduler jobs delete` to remove the old, broken `fonmayang-rain-check` job in `us-central1`.

### 3. CI/CD Integration (Issue 77)
To eliminate the risk of forgetting to manually run the Cloud Scheduler setup script after deployments, we fully integrated it into the GitLab CI/CD pipeline.
1. **Modified `.gitlab-ci.yml`**: Added a new step at the very end of the `deploy_cloud_run` job to execute `./scripts/setup_schedulers.sh`.
2. The script automatically inherits the `$CRON_SECRET` and authentication from the CI environment, ensuring perfect synchronization between Cloud Run deployments and Cloud Scheduler targets.

## Verification
- Checked the command outputs. The jobs were successfully created under `projects/fonmayang/locations/asia-southeast1/jobs/*` with the `ENABLED` state.
- The Cloud Run URL was correctly resolved.
- You can commit and push `.gitlab-ci.yml` to trigger a new deployment and verify the CI/CD automation.
