#!/bin/bash
set -e
# Script to create/update Google Cloud Scheduler jobs pointing to Cloud Run

PROJECT_ID=${GCP_PROJECT:-"fonmayang"}
LOCATION=${GCP_LOCATION:-"asia-southeast1"}
SERVICE_NAME="fontokmai-api"

# 1. Fetch Cloud Run URL
echo "Fetching Cloud Run URL for service '$SERVICE_NAME' in '$LOCATION'..."
BASE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $LOCATION \
  --project $PROJECT_ID \
  --format 'value(status.url)' 2>/dev/null)

if [ -z "$BASE_URL" ]; then
  echo "Error: Could not determine BASE_URL for service '$SERVICE_NAME'."
  exit 1
fi

echo "Found Cloud Run URL: $BASE_URL"

# 2. Get CRON_SECRET from .env or env var
if [ -z "$CRON_SECRET" ]; then
  # Try to read from .env if running locally
  if [ -f "../.env" ]; then
    CRON_SECRET=$(grep -E '^CRON_SECRET=' ../.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
  elif [ -f "./.env" ]; then
    CRON_SECRET=$(grep -E '^CRON_SECRET=' ./.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
  fi
fi

if [ -z "$CRON_SECRET" ]; then
  echo "CRON_SECRET not found in environment or .env. Using fallback."
  CRON_SECRET="default_secret_for_local_testing"
fi

# Function to setup a scheduler job
setup_job() {
  local JOB_NAME=$1
  local SCHEDULE=$2
  local ENDPOINT=$3

  local FULL_URL="${BASE_URL}/api/v1/cron/${ENDPOINT}"
  
  echo "--------------------------------------------------"
  echo "Configuring job: $JOB_NAME"
  echo "Schedule: $SCHEDULE"
  echo "Target: $FULL_URL"
  
  local DESCRIPTION="⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh"
  
  # Check if exists
  if gcloud scheduler jobs describe $JOB_NAME --location=$LOCATION --project=$PROJECT_ID > /dev/null 2>&1; then
    echo "Updating existing job..."
    gcloud scheduler jobs update http $JOB_NAME \
      --location=$LOCATION \
      --project=$PROJECT_ID \
      --schedule="$SCHEDULE" \
      --uri="$FULL_URL" \
      --http-method="POST" \
      --update-headers="Content-Type=application/json,X-Cron-Secret=$CRON_SECRET" \
      --time-zone="Asia/Bangkok" \
      --max-retry-attempts=0 \
      --description="$DESCRIPTION"
  else
    echo "Creating new job..."
    gcloud scheduler jobs create http $JOB_NAME \
      --location=$LOCATION \
      --project=$PROJECT_ID \
      --schedule="$SCHEDULE" \
      --uri="$FULL_URL" \
      --http-method="POST" \
      --headers="Content-Type=application/json,X-Cron-Secret=$CRON_SECRET" \
      --time-zone="Asia/Bangkok" \
      --max-retry-attempts=0 \
      --description="$DESCRIPTION"
  fi
}

# 3. Setup Jobs
setup_job "fonmayang-check-rain" "*/20 * * * *" "check-rain"
setup_job "fonmayang-disasters-freq" "*/5 * * * *" "check-disasters-frequent"
setup_job "fonmayang-disasters-infreq" "0 * * * *" "check-disasters-infrequent"
setup_job "fonmayang-fetch-radar" "*/5 * * * *" "fetch-tmd-radar"

echo "=================================================="
echo "✅ Cloud Scheduler configuration complete!"
