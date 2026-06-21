#!/bin/bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-fontokmai-api}"
OUTPUT_MODE="table"

usage() {
  cat <<'EOF'
Usage:
  audit_window_2026-06-21.sh [--start UTC_ISO8601] [--end UTC_ISO8601] [--json]

Examples:
  audit_window_2026-06-21.sh
  audit_window_2026-06-21.sh --start 2026-06-20T18:10:00Z --end 2026-06-20T18:30:00Z
  audit_window_2026-06-21.sh --start 2026-06-20T18:10:00Z --end 2026-06-20T18:30:00Z --json

Notes:
  - The defaults cover 2026-06-21 01:10-01:30 Asia/Bangkok.
  - Times must be UTC in ISO-8601 format, e.g. 2026-06-20T18:10:00Z.
EOF
}

START_UTC="2026-06-20T18:10:00Z"
END_UTC="2026-06-20T18:30:00Z"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start)
      START_UTC="${2:-}"
      shift 2
      ;;
    --end)
      END_UTC="${2:-}"
      shift 2
      ;;
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${START_UTC}" || -z "${END_UTC}" ]]; then
  echo "Both --start and --end are required when overriding the default window." >&2
  usage >&2
  exit 1
fi

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
  local query="$1"

  if [ "$OUTPUT_MODE" = "json" ]; then
    gcloud logging read "$query" \
      --project="$PROJECT_ID" \
      --limit=200 \
      --format=json
  else
    gcloud logging read "$query" \
      --project="$PROJECT_ID" \
      --limit=200 \
      --format='table(timestamp,severity,resource.type,resource.labels.service_name,resource.labels.revision_name,textPayload,jsonPayload.message)'
  fi
}

run_metric_query() {
  local metric_type="$1"
  local value_field="$2"

  if [ "$OUTPUT_MODE" = "json" ]; then
    gcloud alpha monitoring time-series list \
      --project="$PROJECT_ID" \
      --filter="metric.type=\"${metric_type}\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"" \
      --interval="start=${START_UTC},end=${END_UTC}" \
      --format=json
  else
    gcloud alpha monitoring time-series list \
      --project="$PROJECT_ID" \
      --filter="metric.type=\"${metric_type}\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"" \
      --interval="start=${START_UTC},end=${END_UTC}" \
      --format="table(point.properties.interval.startTime,point.value.${value_field},resource.labels.revision_name,metric.labels.response_code_class)"
  fi
}

log_section "Audit Window"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Window (UTC): $START_UTC -> $END_UTC"
echo "Window (Asia/Bangkok): 2026-06-21 01:10 -> 01:30"

run_or_warn "Cloud Run request logs" run_logging_query \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Budget webhook logs" run_logging_query \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"BudgetAlert\" OR jsonPayload.message:\"BudgetAlert\" OR textPayload:\"/budget-alert\" OR jsonPayload.message:\"/budget-alert\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Internal webhook / worker logs" run_logging_query \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"internal\" OR jsonPayload.message:\"internal\" OR textPayload:\"webhook\" OR jsonPayload.message:\"webhook\" OR textPayload:\"worker\" OR jsonPayload.message:\"worker\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\""

run_or_warn "Pub/Sub delivery logs" run_logging_query \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (textPayload:\"pubsub\" OR jsonPayload.message:\"pubsub\" OR resource.type=\"pubsub_subscription\" OR resource.type=\"pubsub_topic\")"

run_or_warn "Cloud Scheduler logs" run_logging_query \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (resource.type=\"cloud_scheduler_job\" OR textPayload:\"cloudscheduler\" OR jsonPayload.message:\"cloudscheduler\")"

run_or_warn "Cloud Run request count" run_metric_query \
  "run.googleapis.com/request_count" \
  "int64Value"

run_or_warn "Cloud Run request latency" run_metric_query \
  "run.googleapis.com/request_latencies" \
  "doubleValue"

run_or_warn "Cloud Run instance count" run_metric_query \
  "run.googleapis.com/container/instance_count" \
  "int64Value"

run_or_warn "Cloud Run memory utilization" run_metric_query \
  "run.googleapis.com/container/memory/utilizations" \
  "doubleValue"

run_or_warn "Cloud Run CPU utilization" run_metric_query \
  "run.googleapis.com/container/cpu/utilizations" \
  "doubleValue"

run_or_warn "Cloud Tasks logs" run_logging_query \
  "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (resource.type=\"cloud_tasks_queue\" OR textPayload:\"cloudtasks\" OR jsonPayload.message:\"cloudtasks\")"

echo
echo "Audit complete."
