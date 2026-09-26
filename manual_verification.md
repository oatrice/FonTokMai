# Manual Verification Plan: GitHub Actions & GitLab CI Pipeline Parity

- **Issue ID**: #341 (Closes #341)
- **Target Branch**: `dev`
- **Release Version**: `0.77.1`
- **Updated Date**: 2026-09-26

---

## 🎯 Verification Objectives
Verify that the GitHub Actions workflows (`.github/workflows/main.yml`, `.github/workflows/cloudrun_config.yml`, and `.github/workflows/cleanup.yml`) provide 100% functional parity with the GitLab CI pipeline (`.gitlab-ci.yml`), including:
1. Canonical deployment script execution (`backend/deploy/deploy_cloudrun.sh`) with NeonDB backend and all 14+ new environment variables.
2. Missing verification and test gates (`check_docs_updated`, `test_security`).
3. Manual pipeline execution triggers (`workflow_dispatch`).
4. Automated release tagging on `main` (`auto_git_tag`).
5. E2E Playwright HTML test report archiving and robust frontend test CI flags.

---

## 🔐 GitHub Repository Secrets & Variables Checklist

To ensure GitHub Actions can execute and deploy smoothly, ensure the following Secrets and Variables are configured under **GitHub Repository Settings > Secrets and variables > Actions**:

### 1. Required Secrets (`Repository secrets`)
| Secret Name | Description / Source |
|---|---|
| `GCP_SA_KEY` | Google Cloud Service Account JSON Key (Base64 or Raw JSON with Cloud Run Admin, Artifact Registry Admin, Compute Admin) |
| `GCP_PROJECT_ID` | Google Cloud Project ID (e.g., `fonmayang`) |
| `CI_TELEGRAM_BOT_TOKEN` | Telegram Bot Token for CI notifications |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID for CI notifications |
| `TELEGRAM_BOT_TOKEN` | Production Telegram Bot Token |
| `DEV_TELEGRAM_BOT_TOKEN` | Development/Staging Telegram Bot Token |
| `DATABASE_URL` | NeonDB / PostgreSQL connection string |
| `DATABASE_URL_DEV` | (Optional) Dedicated Development Database URL |
| `DATABASE_URL_STAGING` | (Optional) Dedicated Staging Database URL |
| `DATABASE_URL_PROD` | (Optional) Dedicated Production Database URL |
| `CRON_SECRET` | Secret token for authorized Cloud Scheduler calls |
| `RAINBOW_API_KEY` | Rainbow Weather API Key |
| `TOMORROW_API_KEY` | Tomorrow.io API Key |
| `XWEATHER_CLIENT_ID` | Xweather Client ID |
| `XWEATHER_CLIENT_SECRET` | Xweather Client Secret |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `OCR_SPACE_API_KEY` | OCR Space API Key |
| `WORKER_SECRET` | Internal worker shared secret |
| `INTERNAL_WEBHOOK_SECRET` | Internal EMSC / radar webhook secret |
| `ADMIN_BYPASS_PASSWORD` | Administrator bypass password |
| `GCP_BILLING_ACCOUNT_ID` | GCP Billing Account ID |
| `GCP_BUDGET_DISPLAY_NAME` | GCP Budget display name |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API Channel Access Token |
| `LINE_CHANNEL_SECRET` | LINE Messaging API Channel Secret |
| `STRIPE_SECRET_KEY` | Stripe Secret API Key |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook Signing Secret |
| `HASH_SALT` | Cryptographic salt for sensitive hashing |
| `FIREBASE_STORAGE_BUCKET` | Cloud Storage bucket name |

### 2. Configuration Variables (`Repository variables`)
| Variable Name | Default Value | Description |
|---|---|---|
| `XWEATHER_ENABLED` | `false` | Enable or disable Xweather API queries |
| `ALERT_COOLDOWN_MINUTES` | `30` | Minimum cooldown between proactive rain alerts |
| `RAIN_TRIGGER_THRESHOLD_MM` | `0.5` | Rain threshold to trigger alerts |
| `STORAGE_BACKEND` | `neondb` | Storage backend (ensured as `neondb` in deploy script) |
| `GRPC_ENABLE_FORK_SUPPORT` | `1` | gRPC multi-threading / fork support |
| `GCP_BILLING_BIGQUERY_DATASET` | `billing_export` | BigQuery dataset name for billing data |
| `FORCE_GCP_REAL_DATA` | `false` | Force real BigQuery data on non-prod environments |
| `USE_LOCAL_FIXTURES` | `false` | Use local radar fixtures |

---

## 🧪 Step-by-Step Verification Scenarios

### Scenario 1: Syntax & Environment Sync Verification (Local)
1. **Step 1: Validate YAML Workflow Syntax**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/main.yml')); yaml.safe_load(open('.github/workflows/cloudrun_config.yml')); yaml.safe_load(open('.github/workflows/cleanup.yml')); print('✅ All YAML files are syntactically valid!')"
   ```
   - **Expected Outcome:**
     - Exit Code: `0`
     - Output: `✅ All YAML files are syntactically valid!`

2. **Step 2: Run Deployment Environment Synchronization Test**
   ```bash
   pytest backend/tests/test_deploy_env_sync.py -v
   ```
   - **Expected Outcome:**
     - 1 passed in < 0.1s. Confirms `backend/deploy/deploy_cloudrun.sh` contains all variables required by `.env.example`.

3. **Step 3: Run Security & Radar Regression Test Suite**
   ```bash
   pytest backend/tests/test_radar_security.py backend/tests/test_radar_router_fixes.py backend/tests/test_performance_polygon.py -v --tb=short
   ```
   - **Expected Outcome:**
     - 31 passed in ~3s. Verifies the exact suite executed by the new `test_security` job.

---

### Scenario 2: Documentation & Version Sync Gate Verification (`check_docs_updated`)
1. **Step 1: Inspect PR Check Logic**
   - When a Pull Request is opened targeting `staging` or `main`:
     - Checks if `CHANGELOG.md` is modified in the PR diff.
     - Checks if `VERSION` is modified in the PR diff.
     - Checks if `backend/VERSION` is updated if `backend/` files changed.
     - Checks if `frontend/package.json` version matches if `frontend/` files changed.
   - **Expected Outcome:**
     - If all files are present: Job passes with `🎉 All required documentation files are updated and synchronized with the latest code changes!`.
     - If any required file is missing: Job fails with exit code `1` and descriptive error message.

---

### Scenario 3: Cloud Run Deployment Parity Verification (`deploy_cloud_run`)
1. **Step 1: Validate Deployment Command Invocations**
   - The job no longer calls `gcloud run deploy fontokmai-api ...` directly with hardcoded inline parameters.
   - Instead, it delegates to `./deploy/deploy_cloudrun.sh`, which:
     1. Automatically detects `ENVIRONMENT` (`development`, `staging`, `production`) and `CLOUD_RUN_SERVICE` (`fontokmai-api-dev`, `fontokmai-api-staging`, `fontokmai-api`) from `CI_COMMIT_BRANCH`.
     2. Sets `min-instances: 1` and `--no-cpu-throttling` to prevent cold starts.
     3. Copies `VERSION` to `backend/VERSION`.
     4. Runs `scripts/cleanup_artifact_registry.sh` immediately after deployment to eliminate stale container images.
     5. Updates the Telegram webhook URL and Cloud Scheduler jobs on `main`.

---

### Scenario 4: Automated Tagging Verification (`auto_git_tag`)
1. **Step 1: Tagging on `main` Branch Push**
   - When code is pushed/merged into `main`:
     - Reads `VERSION` (e.g. `0.77.1`).
     - Checks if git tag `v0.77.1` exists.
     - If not, automatically creates `v0.77.1` with message `Release v0.77.1` and pushes it to GitHub.
