#!/bin/bash
# =============================================================================
# Script: setup_queue_alert.sh
# Issue:  #74 — Cloud Tasks Queue Monitoring
# Description:
#   สร้าง Cloud Monitoring Alert Policy เพื่อตรวจสอบ Queue Depth 
#   ของ Cloud Tasks หากมี tasks สะสมค้างในคิวเกิน 100 tasks เป็นเวลา 5 นาที
#   จะเกิด Alert เพื่อให้ทีมทราบว่าระบบประมวลผลมีปัญหา
#
# Required ENV Vars:
#   GCP_PROJECT_ID          - GCP Project ID
#   GCP_LOCATION            - GCP Location (default: asia-southeast1)
#   CLOUD_TASKS_QUEUE       - Queue Name (default: webhook-worker-queue)
# =============================================================================

set -e

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
LOCATION="${GCP_LOCATION:-asia-southeast1}"
QUEUE_NAME="${CLOUD_TASKS_QUEUE:-webhook-worker-queue}"

echo "=================================================="
echo "📊 Setting up Queue Monitoring Alert Policy"
echo "Project: $PROJECT_ID"
echo "Queue Name: $QUEUE_NAME"
echo "Location: $LOCATION"
echo "Threshold: > 100 tasks for 5 minutes"
echo "=================================================="

# ─────────────────────────────────────────────────────
# 1. Define the Alert Policy JSON
# ─────────────────────────────────────────────────────
POLICY_DISPLAY_NAME="High Queue Depth Alert - ${QUEUE_NAME}"

# สร้าง temp file สำหรับ JSON policy
POLICY_CONFIG_FILE="/tmp/queue_alert_policy.json"

cat <<EOF > "$POLICY_CONFIG_FILE"
{
  "displayName": "${POLICY_DISPLAY_NAME}",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Queue Depth > 100 for 5 minutes",
      "conditionThreshold": {
        "filter": "metric.type=\"cloudtasks.googleapis.com/queue/depth\" AND resource.type=\"cloud_tasks_queue\" AND resource.labels.queue_id=\"${QUEUE_NAME}\" AND resource.labels.location=\"${LOCATION}\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 100,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_NONE",
            "perSeriesAligner": "ALIGN_MAX"
          }
        ]
      }
    }
  ],
  "severity": "CRITICAL"
}
EOF

# ─────────────────────────────────────────────────────
# 2. Check if Policy exists and Create/Update
# ─────────────────────────────────────────────────────
echo ""
echo "🔍 Checking existing policies..."

# ค้นหา policy เดิมผ่าน gcloud alpha monitoring policies
EXISTING_POLICY=$(gcloud alpha monitoring policies list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName=\"$POLICY_DISPLAY_NAME\"" 2>/dev/null | head -1)

if [ -n "$EXISTING_POLICY" ]; then
  echo "  🔄 Policy '$POLICY_DISPLAY_NAME' exists ($EXISTING_POLICY). Updating..."
  gcloud alpha monitoring policies update "$EXISTING_POLICY" \
    --project="$PROJECT_ID" \
    --policy-from-file="$POLICY_CONFIG_FILE"
  echo "  ✅ Alert Policy updated."
else
  echo "  ✨ Creating new policy '$POLICY_DISPLAY_NAME'..."
  gcloud alpha monitoring policies create \
    --project="$PROJECT_ID" \
    --policy-from-file="$POLICY_CONFIG_FILE"
  echo "  ✅ Alert Policy created."
fi

rm -f "$POLICY_CONFIG_FILE"

echo ""
echo "=================================================="
echo "🎉 Queue Monitoring Setup Complete!"
echo "   ⚠️ IMPORTANT NEXT STEP:"
echo "   You must link a Notification Channel (Email, Slack, Pub/Sub -> Telegram) "
echo "   to this policy in the Google Cloud Console."
echo ""
echo "   Go to: Monitoring -> Alerting -> Policies -> '$POLICY_DISPLAY_NAME'"
echo "   Click Edit, and add your preferred Notification Channel."
echo "=================================================="
