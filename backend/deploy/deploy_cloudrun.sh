#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Safety Guard: Prevent accidental local runs
if [ -z "${CI:-}" ]; then
  if [ "${1:-}" != "--danger-local-run" ]; then
    echo "❌ ERROR: This script is intended to be run by GitLab CI/CD."
    echo "If you absolutely must run this locally, pass the '--danger-local-run' flag."
    echo "Usage: ./deploy_cloudrun.sh --danger-local-run"
    exit 1
  fi
  echo "⚠️ WARNING: Deploying Cloud Run locally because --danger-local-run was provided."
fi

if [ -f "$SCRIPT_DIR/cloudrun.env" ]; then
  # shellcheck disable=SC1091
  set -a
  source "$SCRIPT_DIR/cloudrun.env"
  set +a
fi

: "${CLOUD_RUN_SERVICE:=fontokmai-api}"
: "${CLOUD_RUN_REGION:=asia-southeast1}"
: "${CLOUD_RUN_SERVICE_ACCOUNT:=cloud-run-runtime@fonmayang.iam.gserviceaccount.com}"
: "${CLOUD_RUN_ALLOW_UNAUTHENTICATED:=true}"
: "${CLOUD_RUN_MEMORY:=1Gi}"
: "${CLOUD_RUN_CPU:=1}"
: "${CLOUD_RUN_TIMEOUT:=300}"
: "${CLOUD_RUN_MIN_INSTANCES:=1}"
: "${CLOUD_RUN_MAX_INSTANCES:=2}"
: "${CLOUD_RUN_CONCURRENCY:=40}"
: "${CLOUD_RUN_CPU_BOOST:=true}"
: "${CLOUD_RUN_NO_CPU_THROTTLING:=true}"

cd "$SCRIPT_DIR/.."

echo "Deploying ${CLOUD_RUN_SERVICE} to Cloud Run"

ALLOW_FLAG="--allow-unauthenticated"
if [ "$CLOUD_RUN_ALLOW_UNAUTHENTICATED" != "true" ]; then
  ALLOW_FLAG="--no-allow-unauthenticated"
fi

CPU_BOOST_FLAG="--cpu-boost"
if [ "$CLOUD_RUN_CPU_BOOST" != "true" ]; then
  CPU_BOOST_FLAG="--no-cpu-boost"
fi

CPU_THROTTLING_FLAG="--no-cpu-throttling"
if [ "$CLOUD_RUN_NO_CPU_THROTTLING" != "true" ]; then
  CPU_THROTTLING_FLAG="--cpu-throttling"
fi

gcloud run deploy "$CLOUD_RUN_SERVICE" \
  --source . \
  --service-account="$CLOUD_RUN_SERVICE_ACCOUNT" \
  --region "$CLOUD_RUN_REGION" \
  $ALLOW_FLAG \
  --memory "$CLOUD_RUN_MEMORY" \
  --cpu "$CLOUD_RUN_CPU" \
  --timeout "$CLOUD_RUN_TIMEOUT" \
  --service-min-instances "$CLOUD_RUN_MIN_INSTANCES" \
  --service-max-instances "$CLOUD_RUN_MAX_INSTANCES" \
  --concurrency "$CLOUD_RUN_CONCURRENCY" \
  $CPU_BOOST_FLAG \
  $CPU_THROTTLING_FLAG \
  --set-env-vars "\
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},\
DEV_TELEGRAM_BOT_TOKEN=${DEV_TELEGRAM_BOT_TOKEN:-},\
RAINBOW_API_KEY=${RAINBOW_API_KEY},\
TOMORROW_API_KEY=${TOMORROW_API_KEY},\
XWEATHER_CLIENT_ID=${XWEATHER_CLIENT_ID},\
XWEATHER_CLIENT_SECRET=${XWEATHER_CLIENT_SECRET},\
XWEATHER_ENABLED=${XWEATHER_ENABLED},\
DEVELOPER_CHAT_IDS=${DEVELOPER_CHAT_IDS},\
ENVIRONMENT=production,\
CRON_SECRET=${CRON_SECRET},\
STORAGE_BACKEND=firestore,\
FIREBASE_STORAGE_BUCKET=${FIREBASE_STORAGE_BUCKET},\
ALERT_COOLDOWN_MINUTES=${ALERT_COOLDOWN_MINUTES},\
RAIN_TRIGGER_THRESHOLD_MM=${RAIN_TRIGGER_THRESHOLD_MM},\
GEMINI_API_KEY=${GEMINI_API_KEY},\
OCR_SPACE_API_KEY=${OCR_SPACE_API_KEY},\
WORKER_SECRET=${WORKER_SECRET},\
WORKER_BASE_URL=${WORKER_BASE_URL},\
INTERNAL_WEBHOOK_SECRET=${INTERNAL_WEBHOOK_SECRET},\
ADMIN_BYPASS_PASSWORD=${ADMIN_BYPASS_PASSWORD},\
GCP_BILLING_ACCOUNT_ID=${GCP_BILLING_ACCOUNT_ID},\
GCP_BUDGET_DISPLAY_NAME=${GCP_BUDGET_DISPLAY_NAME},\
LINE_CHANNEL_ACCESS_TOKEN=${LINE_CHANNEL_ACCESS_TOKEN},\
LINE_CHANNEL_SECRET=${LINE_CHANNEL_SECRET},\
GRPC_ENABLE_FORK_SUPPORT=${GRPC_ENABLE_FORK_SUPPORT},\
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET},\
GCP_PROJECT_ID=${GCP_PROJECT_ID:-},\
GCP_BILLING_BIGQUERY_DATASET=${GCP_BILLING_BIGQUERY_DATASET:-},\
USE_LOCAL_FIXTURES=${USE_LOCAL_FIXTURES:-false}"
