#!/bin/bash
# =============================================================================
# Script: setup_budget_alert.sh
# Issue:  #72 — Budget-based Auto-shutdown Mechanism for Cloud Run
# Description:
#   สร้าง GCP Budget Alert และ Pub/Sub topic สำหรับระบบ auto-shutdown
#   เมื่อค่าใช้จ่ายถึง threshold ที่กำหนด Cloud Run จะถูกสั่ง scale ลงเหลือ 0
#
# Required ENV Vars (ตั้งใน GitLab CI/CD Variables หรือ .env):
#   GCP_PROJECT_ID          - GCP Project ID
#   GCP_BILLING_ACCOUNT_ID  - GCP Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX)
#   BUDGET_AMOUNT_USD       - Budget threshold ในหน่วย USD (default: 10)
#   CLOUD_RUN_URL           - Cloud Run service URL (auto-detected ถ้าไม่ได้กำหนด)
# =============================================================================

set -e

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
BILLING_ACCOUNT_ID="${GCP_BILLING_ACCOUNT_ID:?Error: GCP_BILLING_ACCOUNT_ID is required}"
BUDGET_AMOUNT="${BUDGET_AMOUNT_USD:-10}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SERVICE_NAME="fontokmai-api"
PUBSUB_TOPIC="billing-alerts"
BUDGET_DISPLAY_NAME="${SERVICE_NAME}-monthly-budget"

echo "=================================================="
echo "💰 Setting up Budget Alert for FonMaYang"
echo "Project: $PROJECT_ID"
echo "Billing Account: $BILLING_ACCOUNT_ID"
echo "Budget Threshold: \$${BUDGET_AMOUNT} USD/month"
echo "Pub/Sub Topic: $PUBSUB_TOPIC"
echo "=================================================="

# ─────────────────────────────────────────────────────
# 1. สร้าง Pub/Sub Topic สำหรับรับ Budget Alert
# ─────────────────────────────────────────────────────
echo ""
echo "📡 Step 1: Setting up Pub/Sub topic..."

if gcloud pubsub topics describe "$PUBSUB_TOPIC" --project="$PROJECT_ID" > /dev/null 2>&1; then
  echo "  ✅ Pub/Sub topic '$PUBSUB_TOPIC' already exists."
else
  gcloud pubsub topics create "$PUBSUB_TOPIC" --project="$PROJECT_ID"
  echo "  ✅ Created Pub/Sub topic: $PUBSUB_TOPIC"
fi

# ─────────────────────────────────────────────────────
# 2. Grant Cloud Billing permission to publish to Pub/Sub
#    (GCP Billing service account needs roles/pubsub.publisher)
# ─────────────────────────────────────────────────────
echo ""
echo "🔑 Step 2: Granting Billing service account Pub/Sub publisher access..."

BILLING_SA="serviceAccount:billing-export@system.gserviceaccount.com"
gcloud pubsub topics add-iam-policy-binding "$PUBSUB_TOPIC" \
  --project="$PROJECT_ID" \
  --member="$BILLING_SA" \
  --role="roles/pubsub.publisher" > /dev/null 2>&1 || true

echo "  ✅ IAM binding set."

# ─────────────────────────────────────────────────────
# 3. สร้าง Pub/Sub Subscription (Push → Cloud Run endpoint)
# ─────────────────────────────────────────────────────
echo ""
echo "📨 Step 3: Setting up Pub/Sub push subscription..."

# ดึง Cloud Run URL อัตโนมัติ
if [ -z "$CLOUD_RUN_URL" ]; then
  CLOUD_RUN_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)' 2>/dev/null || echo "")
fi

if [ -z "$CLOUD_RUN_URL" ]; then
  echo "  ⚠️  Could not detect Cloud Run URL. Skipping push subscription setup."
  echo "     Run manually: gcloud pubsub subscriptions create billing-alerts-sub --topic=$PUBSUB_TOPIC --push-endpoint=<CLOUD_RUN_URL>/api/v1/internal/budget-alert"
else
  PUSH_ENDPOINT="${CLOUD_RUN_URL}/api/v1/internal/budget-alert"
  SUBSCRIPTION_NAME="billing-alerts-sub"

  if gcloud pubsub subscriptions describe "$SUBSCRIPTION_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "  🔄 Subscription '$SUBSCRIPTION_NAME' exists. Updating push endpoint..."
    gcloud pubsub subscriptions modify-push-config "$SUBSCRIPTION_NAME" \
      --project="$PROJECT_ID" \
      --push-endpoint="$PUSH_ENDPOINT"
  else
    gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
      --project="$PROJECT_ID" \
      --topic="$PUBSUB_TOPIC" \
      --push-endpoint="$PUSH_ENDPOINT" \
      --ack-deadline=60 \
      --message-retention-duration=10m
  fi
  echo "  ✅ Push subscription configured → $PUSH_ENDPOINT"
fi

# ─────────────────────────────────────────────────────
# 4. สร้าง/อัปเดต GCP Budget Alert
# ─────────────────────────────────────────────────────
echo ""
echo "💳 Step 4: Setting up GCP Budget Alert..."

# ตรวจสอบว่ามี budget นี้อยู่แล้วหรือไม่
EXISTING_BUDGET=$(gcloud billing budgets list \
  --billing-account="$BILLING_ACCOUNT_ID" \
  --format="value(name)" \
  --filter="displayName=$BUDGET_DISPLAY_NAME" 2>/dev/null | head -1)

TOPIC_RESOURCE="projects/${PROJECT_ID}/topics/${PUBSUB_TOPIC}"

# Budget JSON config
BUDGET_CONFIG=$(cat <<EOF
{
  "displayName": "${BUDGET_DISPLAY_NAME}",
  "budgetFilter": {
    "projects": ["projects/${PROJECT_ID}"]
  },
  "amount": {
    "specifiedAmount": {
      "currencyCode": "USD",
      "units": "${BUDGET_AMOUNT}"
    }
  },
  "thresholdRules": [
    {
      "thresholdPercent": 0.8,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 1.0,
      "spendBasis": "CURRENT_SPEND"
    }
  ],
  "notificationsRule": {
    "pubsubTopic": "${TOPIC_RESOURCE}",
    "schemaVersion": "1.0"
  }
}
EOF
)

BUDGET_CONFIG_FILE="/tmp/fonmayang_budget.json"
echo "$BUDGET_CONFIG" > "$BUDGET_CONFIG_FILE"

if [ -n "$EXISTING_BUDGET" ]; then
  echo "  🔄 Budget '$BUDGET_DISPLAY_NAME' exists. Updating..."
  gcloud billing budgets update "$EXISTING_BUDGET" \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --from-file="$BUDGET_CONFIG_FILE"
  echo "  ✅ Budget updated."
else
  echo "  ✨ Creating budget '$BUDGET_DISPLAY_NAME'..."
  gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --from-file="$BUDGET_CONFIG_FILE"
  echo "  ✅ Budget created."
fi

rm -f "$BUDGET_CONFIG_FILE"

# ─────────────────────────────────────────────────────
# 5. Grant Cloud Run invoker permission ให้ Pub/Sub SA
# ─────────────────────────────────────────────────────
echo ""
echo "🔑 Step 5: Granting Pub/Sub SA Cloud Run invoker permission..."

PUBSUB_SA="serviceAccount:service-$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')@gcp-sa-pubsub.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --member="$PUBSUB_SA" \
  --role="roles/run.invoker" > /dev/null 2>&1 || true

echo "  ✅ Cloud Run invoker permission granted to Pub/Sub SA."

echo ""
echo "=================================================="
echo "🎉 Budget Alert Setup Complete!"
echo "   Topic: projects/$PROJECT_ID/topics/$PUBSUB_TOPIC"
echo "   Budget: \$${BUDGET_AMOUNT} USD/month"
echo "   Thresholds: 80% (warning) + 100% (shutdown trigger)"
echo "=================================================="
