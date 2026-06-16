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
