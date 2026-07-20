#!/bin/bash
set -e

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
  echo "📥 Loading environment variables from .env..."
  set -a; source .env; set +a
elif [ -f "../.env" ]; then
  echo "📥 Loading environment variables from ../.env..."
  set -a; source ../.env; set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SERVICE_NAME="fontokmai-api"

echo "=================================================="
echo "🔒 Disabling Public Access to $SERVICE_NAME"
echo "=================================================="

gcloud run services remove-iam-policy-binding "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet

echo "✅ Public access disabled successfully."

# Send Telegram message if token exists
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$DEVELOPER_CHAT_IDS" ]; then
  echo "📡 Sending Telegram notification..."
  
  # Replace commas with spaces to iterate
  CHAT_IDS=$(echo "$DEVELOPER_CHAT_IDS" | tr ',' ' ')
  
  for CHAT_ID in $CHAT_IDS; do
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -H "Content-Type: application/json" \
      -d "{
        \"chat_id\": \"${CHAT_ID}\",
        \"text\": \"🔒 <b>Service Access Restricted</b>\n\nระบบ <code>${SERVICE_NAME}</code> ถูกยกเลิกสิทธิ์ Public Access แล้ว (โหมดส่วนตัว/Private)\",
        \"parse_mode\": \"HTML\"
      }" > /dev/null
  done
  echo "✅ Telegram notifications sent."
else
  echo "⚠️ TELEGRAM_BOT_TOKEN or DEVELOPER_CHAT_IDS not found in .env. Skipping notification."
fi
