#!/bin/bash
# Script to deploy the Telegram Alert Cloud Function

set -e

# Try to load .env from the project root
ENV_FILE="../../.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading variables from $ENV_FILE"
    # Read .env file, ignoring comments and exporting valid assignments
    set -a
    source <(grep -v '^#' "$ENV_FILE" | grep -v '^\s*$')
    set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-fonmayang}"
REGION="${GCP_REGION:-asia-southeast1}"
TOPIC_NAME="monitoring-alerts"
FUNCTION_NAME="telegram-monitoring-alert"

# Check if required environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN environment variable is not set and was not found in $ENV_FILE."
    echo "Please run: export TELEGRAM_BOT_TOKEN='your_token'"
    exit 1
fi

if [ -z "$DEVELOPER_CHAT_IDS" ]; then
    echo "Error: DEVELOPER_CHAT_IDS environment variable is not set."
    echo "Please run: export DEVELOPER_CHAT_IDS='id1,id2'"
    exit 1
fi

echo "=================================================="
echo "🚀 Deploying Telegram Alert Cloud Function"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Topic: $TOPIC_NAME"
echo "=================================================="

# 1. Create Pub/Sub topic if it doesn't exist
echo "🔍 Checking for Pub/Sub topic '$TOPIC_NAME'..."
if ! gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✨ Creating topic '$TOPIC_NAME'..."
    gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT_ID"
else
    echo "✅ Topic '$TOPIC_NAME' already exists."
fi

# 2. Deploy Cloud Function
echo "📦 Deploying Cloud Function '$FUNCTION_NAME'..."
gcloud functions deploy "$FUNCTION_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --gen2 \
    --runtime=python311 \
    --source=. \
    --entry-point=telegram_pubsub_handler \
    --trigger-topic="$TOPIC_NAME" \
    --set-env-vars="TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,DEVELOPER_CHAT_IDS=$DEVELOPER_CHAT_IDS" \
    --quiet

echo "=================================================="
echo "🎉 Deployment Complete!"
echo ""
echo "⚠️ IMPORTANT NEXT STEP:"
echo "Go to GCP Console -> Monitoring -> Alerting -> Edit Notification Channels"
echo "Create a new 'Pub/Sub' notification channel and point it to the topic: $TOPIC_NAME"
echo "Then attach this channel to your Alert Policies."
echo "=================================================="
