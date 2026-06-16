#!/bin/bash
# Script to initialize and configure Google Cloud resources for FonMaYang

PROJECT_ID=${GCP_PROJECT:-"fonmayang"}
LOCATION=${GCP_LOCATION:-"asia-southeast1"}
QUEUE_NAME=${CLOUD_TASKS_QUEUE:-"webhook-worker-queue"}

echo "=================================================="
echo "☁️  Configuring Google Cloud Tasks"
echo "Project: $PROJECT_ID | Location: $LOCATION"
echo "=================================================="

# Check if queue exists
gcloud tasks queues describe $QUEUE_NAME --location=$LOCATION > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "🔄 Queue '$QUEUE_NAME' already exists. Updating configuration..."
  gcloud tasks queues update $QUEUE_NAME \
    --location=$LOCATION \
    --max-attempts=3 \
    --max-backoff=60s
  echo "✅ Update successful!"
else
  echo "✨ Creating new queue '$QUEUE_NAME'..."
  gcloud tasks queues create $QUEUE_NAME \
    --location=$LOCATION \
    --max-attempts=3 \
    --max-backoff=60s
  echo "✅ Creation successful!"
fi

# ─────────────────────────────────────────────────────
# Cloud Logging Exclusion Filters (Issue #69)
# Reduce billing leak from high-frequency log ingestion
# ─────────────────────────────────────────────────────
echo ""
echo "📋 Configuring Cloud Logging exclusion filters..."

# Exclusion 1: EMSC WebSocket high-frequency streaming noise
EXCLUSION_NAME="emsc-websocket-debug-noise"
if gcloud logging exclusions describe "$EXCLUSION_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
  echo "  🔄 Log exclusion '$EXCLUSION_NAME' already exists. Skipping."
else
  gcloud logging exclusions create "$EXCLUSION_NAME" \
    --project="$PROJECT_ID" \
    --filter='severity=DEBUG AND (jsonPayload.message:"EMSC WebSocket" OR jsonPayload.message:"EMSC: non-JSON")' \
    --description="Exclude EMSC WebSocket high-frequency DEBUG messages (Issue #69 cost optimization)"
  echo "  ✅ Created log exclusion: $EXCLUSION_NAME"
fi

# Exclusion 2: httpx request DEBUG logs (verbose HTTP client logging)
EXCLUSION_NAME_2="httpx-debug-verbose"
if gcloud logging exclusions describe "$EXCLUSION_NAME_2" --project="$PROJECT_ID" > /dev/null 2>&1; then
  echo "  🔄 Log exclusion '$EXCLUSION_NAME_2' already exists. Skipping."
else
  gcloud logging exclusions create "$EXCLUSION_NAME_2" \
    --project="$PROJECT_ID" \
    --filter='severity=DEBUG AND jsonPayload.name="httpx"' \
    --description="Exclude httpx DEBUG-level request/response logs in production (Issue #69)"
  echo "  ✅ Created log exclusion: $EXCLUSION_NAME_2"
fi

echo "  ✅ Cloud Logging exclusion filters configured."
