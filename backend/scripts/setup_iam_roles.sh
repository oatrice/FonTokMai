#!/bin/bash
# Script to configure IAM roles for Cloud Run Service Account

# Change to the backend directory to ensure we can find .env
cd "$(dirname "$0")/.." || exit 1

# Load environment variables from .env if it exists
if [ -f .env ]; then
  echo "📄 Loading variables from .env"
  export $(grep -v '^#' .env | xargs)
else
  echo "⚠️ .env file not found. Make sure environment variables are set."
fi

PROJECT_ID=${GCP_PROJECT:-"fonmayang"}
SA_EMAIL="cloud-run-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Fallback in case GCP_BILLING_ACCOUNT_ID is not in .env
BILLING_ACCOUNT_ID=${GCP_BILLING_ACCOUNT_ID:-""}

echo "=================================================="
echo "🔐 Configuring IAM Roles for Service Account"
echo "Service Account: $SA_EMAIL"
echo "Project: $PROJECT_ID"
echo "=================================================="

echo "1. Granting Firestore / Datastore access..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/datastore.user" \
  --condition=None

echo "2. Granting Cloud Storage Object Admin..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin" \
  --condition=None

echo "3. Granting Cloud Tasks Enqueuer..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudtasks.enqueuer" \
  --condition=None

echo "4. Granting Cloud Monitoring Viewer..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/monitoring.viewer" \
  --condition=None

if [ -n "$BILLING_ACCOUNT_ID" ]; then
  echo "5. Granting Billing Costs Manager..."
  gcloud billing accounts add-iam-policy-binding "$BILLING_ACCOUNT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/billing.costsManager"
else
  echo "⚠️ Skipping Billing Roles: GCP_BILLING_ACCOUNT_ID is not set in .env or environment."
fi

echo "✅ IAM Roles configuration completed."
