#!/bin/bash
# =============================================================================
# Script: setup_log_exclusions.sh
# Description:
#   สร้าง Log Exclusion ใน GCP Cloud Logging เพื่อกรอง (Exclude) HTTP 403 logs 
#   จาก Cloud Run service เพื่อลดปริมาณ log ขยะและประหยัดค่าใช้จ่าย 
#   เมื่อ service ถูก auto-shutdown (revoke allUsers)
# =============================================================================

set -e

if [ -f ".env" ]; then
  set -a; source .env; set +a
elif [ -f "../.env" ]; then
  set -a; source ../.env; set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
SERVICE_NAME="fontokmai-api"
EXCLUSION_NAME="exclude-cloudrun-403s"

echo "=================================================="
echo "🛡️ Setting up Log Exclusion for HTTP 403..."
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "=================================================="

FILTER_EXPRESSION="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND httpRequest.status=403"

# ตรวจสอบว่ามี exclusion นี้อยู่ใน _Default sink หรือไม่
if gcloud logging sinks describe _Default --project="$PROJECT_ID" --format="json" | grep -q "\"name\": \"$EXCLUSION_NAME\""; then
  echo "  🔄 Log exclusion '$EXCLUSION_NAME' already exists in _Default sink. Updating..."
  gcloud logging sinks update _Default \
    --project="$PROJECT_ID" \
    --update-exclusion="name=$EXCLUSION_NAME,description=Exclude 403 logs when auto-shutdown is active,filter=$FILTER_EXPRESSION"
  echo "  ✅ Log exclusion updated."
else
  echo "  ✨ Creating new log exclusion '$EXCLUSION_NAME' in _Default sink..."
  gcloud logging sinks update _Default \
    --project="$PROJECT_ID" \
    --add-exclusion="name=$EXCLUSION_NAME,description=Exclude 403 logs when auto-shutdown is active,filter=$FILTER_EXPRESSION"
  echo "  ✅ Log exclusion created."
fi

echo ""
echo "🎉 Done! HTTP 403 responses will no longer be ingested into Cloud Logging."
echo "Note: The logs are dropped at the router level, saving storage costs."
