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
  local DESCRIPTION=${4:-"⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh"}

  local FULL_URL="${BASE_URL}/api/v1/cron/${ENDPOINT}"
  
  echo "--------------------------------------------------"
  echo "Configuring job: $JOB_NAME"
  echo "Schedule: $SCHEDULE"
  echo "Target: $FULL_URL"
  
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

# 3. Setup Jobs from JSON config
CONFIG_FILE="$(dirname "$0")/../config/schedulers.json"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file not found at $CONFIG_FILE"
  exit 1
fi

echo "Loading jobs from $CONFIG_FILE..."

# Parse JSON using Python and execute setup_job for each entry
python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        jobs = json.load(f)
    for j in jobs:
        # Pass description if it exists, otherwise pass a default
        desc = j.get('description', '⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh')
        # Use single quotes for safe eval, but be careful with single quotes inside strings
        job_name = j['job_name']
        schedule = j['schedule']
        endpoint = j['endpoint_path']
        print(f\"setup_job '{job_name}' '{schedule}' '{endpoint}' '{desc}'\")
except Exception as e:
    print(f'echo \"Failed to parse JSON: {e}\"; exit 1')
" "$CONFIG_FILE" | while read -r cmd; do
    eval "$cmd"
done
echo "✅ Cloud Scheduler configuration complete!"
