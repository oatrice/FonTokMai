#!/bin/bash
# =============================================================================
# Script: setup_cloudrun_alerts.sh
# Issue:  #106 — Deploy GCP Alert Rules for Cloud Run
# =============================================================================

set -e

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-fonmayang}"
LOCATION="${GCP_LOCATION:-asia-southeast1}"

echo "=================================================="
echo "📊 Setting up Cloud Run Monitoring Alert Policies"
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "=================================================="

create_or_update_policy() {
  local display_name="$1"
  local policy_file="$2"
  
  echo "🔍 Checking existing policy: $display_name"
  local existing_policy=$(gcloud alpha monitoring policies list \
    --project="$PROJECT_ID" \
    --format="value(name)" \
    --filter="displayName=\"$display_name\"" 2>/dev/null | head -1)

  if [ -n "$existing_policy" ]; then
    echo "  🔄 Policy exists ($existing_policy). Updating..."
    gcloud alpha monitoring policies update "$existing_policy" \
      --project="$PROJECT_ID" \
      --policy-from-file="$policy_file"
    echo "  ✅ Alert Policy updated."
  else
    echo "  ✨ Creating new policy..."
    gcloud alpha monitoring policies create \
      --project="$PROJECT_ID" \
      --policy-from-file="$policy_file"
    echo "  ✅ Alert Policy created."
  fi
}

TMP_DIR=$(mktemp -d)

# 1. Memory Utilization > 80%
cat <<EOF > "$TMP_DIR/memory_policy.json"
{
  "displayName": "Cloud Run Memory Utilization > 80% - ${SERVICE_NAME}",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Memory > 80% for 5 mins",
      "conditionThreshold": {
        "filter": "metric.type=\"run.googleapis.com/container/memory/utilizations\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.8,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_MAX",
            "perSeriesAligner": "ALIGN_PERCENTILE_99"
          }
        ]
      }
    }
  ],
  "severity": "CRITICAL"
}
EOF

# 2. Latency P95 > 5000ms
cat <<EOF > "$TMP_DIR/latency_policy.json"
{
  "displayName": "Cloud Run Latency P95 > 5000ms - ${SERVICE_NAME}",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Latency P95 > 5000ms for 5 mins",
      "conditionThreshold": {
        "filter": "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 5000,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_PERCENTILE_95",
            "perSeriesAligner": "ALIGN_DELTA"
          }
        ]
      }
    }
  ],
  "severity": "WARNING"
}
EOF

# 3. Error Rate > 5%
cat <<EOF > "$TMP_DIR/error_rate_policy.json"
{
  "displayName": "Cloud Run Error Rate > 5% - ${SERVICE_NAME}",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Error Rate > 5% for 5 mins",
      "conditionThreshold": {
        "filter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND metric.labels.response_code_class=\"5xx\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.05,
        "duration": "300s",
        "denominatorFilter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_SUM",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ],
        "denominatorAggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_SUM",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "severity": "CRITICAL"
}
EOF

# 4. Instance count = 0 (for 3 mins)
cat <<EOF > "$TMP_DIR/instance_count_policy.json"
{
  "displayName": "Cloud Run Instance Count == 0 - ${SERVICE_NAME}",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Active Instances < 1 for 3 mins",
      "conditionThreshold": {
        "filter": "metric.type=\"run.googleapis.com/container/instance_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND metric.labels.state=\"active\"",
        "comparison": "COMPARISON_LT",
        "thresholdValue": 1,
        "duration": "180s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "crossSeriesReducer": "REDUCE_MIN",
            "perSeriesAligner": "ALIGN_MIN"
          }
        ]
      }
    }
  ],
  "severity": "WARNING"
}
EOF

create_or_update_policy "Cloud Run Memory Utilization > 80% - ${SERVICE_NAME}" "$TMP_DIR/memory_policy.json"
create_or_update_policy "Cloud Run Latency P95 > 5000ms - ${SERVICE_NAME}" "$TMP_DIR/latency_policy.json"
create_or_update_policy "Cloud Run Error Rate > 5% - ${SERVICE_NAME}" "$TMP_DIR/error_rate_policy.json"
create_or_update_policy "Cloud Run Instance Count == 0 - ${SERVICE_NAME}" "$TMP_DIR/instance_count_policy.json"

rm -rf "$TMP_DIR"

echo "=================================================="
echo "🎉 Cloud Run Monitoring Setup Complete!"
echo "   ⚠️ IMPORTANT NEXT STEP:"
echo "   You must link a Notification Channel to these policies"
echo "   in the Google Cloud Console -> Monitoring -> Alerting."
echo "=================================================="
