#!/bin/bash
set -euo pipefail

# Audit window:
# 2026-06-21 01:10-01:30 Asia/Bangkok
# UTC window: 2026-06-20T18:10:00Z -> 2026-06-20T18:30:00Z

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-fontokmai-api}"
START_UTC="2026-06-20T18:10:00Z"
END_UTC="2026-06-20T18:30:00Z"

log_section() {
  printf '\n==================================================\n'
  printf '%s\n' "$1"
  printf '==================================================\n'
}

run_or_warn() {
  local title="$1"
  shift

  log_section "$title"
  if "$@"; then
    return 0
  fi

  echo "Command failed: $title" >&2
}

run_logging_query() {
  local title="$1"
  local query="$2"

  gcloud logging read "$query" \
    --project="$PROJECT_ID" \
    --limit=200 \
    --format='table(timestamp,severity,resource.type,resource.labels.service_name,resource.labels.revision_name,textPayload,jsonPayload.message)'
}

run_metric_query() {
  local title="$1"
  local metric_type="$2"
  local value_field="$3"

  gcloud monitoring time-series list \
    --project="$PROJECT_ID" \
    --filter="metric.type=\"${metric_type}\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"" \
    --interval="start=${START_UTC},end=${END_UTC}" \
    --format="table(point.properties.interval.startTime,point.value.${value_field},resource.labels.revision_name,metric.labels.response_code_class)"
}

log_section "Audit Window"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Window (UTC): $START_UTC -> $END_UTC"
echo "Window (Asia/Bangkok): 2026-06-21 01:10 -> 01:30"

run_or_warn "Cloud Run request logs" run_logging_query \
  "Cloud Run request logs" \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Budget webhook logs" run_logging_query \
  "Budget webhook logs" \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"BudgetAlert\" OR jsonPayload.message:\"BudgetAlert\" OR textPayload:\"/budget-alert\" OR jsonPayload.message:\"/budget-alert\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Internal webhook / worker logs" run_logging_query \
  "Internal webhook / worker logs" \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"internal\" OR jsonPayload.message:\"internal\" OR textPayload:\"webhook\" OR jsonPayload.message:\"webhook\" OR textPayload:\"worker\" OR jsonPayload.message:\"worker\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Pub/Sub delivery logs" run_logging_query \
  "Pub/Sub delivery logs" \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (textPayload:\"pubsub\" OR jsonPayload.message:\"pubsub\" OR resource.type=\"pubsub_subscription\" OR resource.type=\"pubsub_topic\")"

run_or_warn "Cloud Scheduler logs" run_logging_query \
  "Cloud Scheduler logs" \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (resource.type=\"cloud_scheduler_job\" OR textPayload:\"cloudscheduler\" OR jsonPayload.message:\"cloudscheduler\")"

run_or_warn "Cloud Run request count" run_metric_query \
  "Cloud Run request count" \
  "run.googleapis.com/request_count" \
  "int64Value"

run_or_warn "Cloud Run request latency" run_metric_query \
  "Cloud Run request latency" \
  "run.googleapis.com/request_latencies" \
  "doubleValue"

run_or_warn "Cloud Run instance count" run_metric_query \
  "Cloud Run instance count" \
  "run.googleapis.com/container/instance_count" \
  "int64Value"

run_or_warn "Cloud Run memory utilization" run_metric_query \
  "Cloud Run memory utilization" \
  "run.googleapis.com/container/memory/utilizations" \
  "doubleValue"

run_or_warn "Cloud Run CPU utilization" run_metric_query \
  "Cloud Run CPU utilization" \
  "run.googleapis.com/container/cpu/utilizations" \
  "doubleValue"

run_or_warn "Cloud Tasks logs" run_logging_query \
  "Cloud Tasks logs" \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (resource.type=\"cloud_tasks_queue\" OR textPayload:\"cloudtasks\" OR jsonPayload.message:\"cloudtasks\")"

echo
echo "Audit complete."
