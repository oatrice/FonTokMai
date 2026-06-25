#!/bin/bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-fontokmai-api}"
OUTPUT_MODE="table"
OUTPUT_DIR=""
SUMMARY_FILE=""
DEBUG_MODE=false
LOG_TIMEOUT_SECONDS=60
LOG_LIMIT=200
LOG_FRESHNESS=""
SECTION_FILTER=""
WINDOW_MINUTES=""
LOG_PROVIDER="ga"
LOG_MODE="gcloud"
METRICS_ONLY=false
METRIC_TIMEOUT_SECONDS=30

usage() {
  cat <<'EOF'
Usage:
  audit_window_2026-06-21.sh [--project PROJECT_ID] [--service SERVICE_NAME] [--output-dir DIR] [--start UTC_ISO8601] [--end UTC_ISO8601] [--json] [--debug] [--timeout SECONDS] [--metric-timeout SECONDS] [--freshness DURATION] [--section NAME] [--window-minutes MINUTES] [--logging-provider ga|beta|alpha] [--logging-mode gcloud|api] [--metrics-only]

Examples:
  audit_window_2026-06-21.sh
  audit_window_2026-06-21.sh --project fonmayang --service fontokmai-api
  audit_window_2026-06-21.sh --output-dir /tmp/audit-run --json
  audit_window_2026-06-21.sh --output-dir /tmp/audit-run --json --debug
  audit_window_2026-06-21.sh --start 2026-06-20T18:10:00Z --end 2026-06-20T18:30:00Z
  audit_window_2026-06-21.sh --start 2026-06-20T18:10:00Z --end 2026-06-20T18:30:00Z --json
  audit_window_2026-06-21.sh --start 2026-06-20T18:10:00Z --end 2026-06-20T18:30:00Z --json --debug --timeout 20
  audit_window_2026-06-21.sh --json --debug --section request_logs --window-minutes 5
  audit_window_2026-06-21.sh --json --metrics-only
  audit_window_2026-06-21.sh --json --logging-provider beta
  audit_window_2026-06-21.sh --json --logging-mode api
  audit_window_2026-06-21.sh --json --metrics-only --metric-timeout 10

Notes:
  - The defaults cover 2026-06-21 01:10-01:30 Asia/Bangkok.
  - Times must be UTC in ISO-8601 format, e.g. 2026-06-20T18:10:00Z.
EOF
}

START_UTC="2026-06-20T18:10:00Z"
END_UTC="2026-06-20T18:30:00Z"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT_ID="${2:-}"
      shift 2
      ;;
    --service)
      SERVICE_NAME="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
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
    --debug)
      DEBUG_MODE=true
      LOG_LIMIT=1
      shift
      ;;
    --timeout)
      LOG_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --metric-timeout)
      METRIC_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --freshness)
      LOG_FRESHNESS="${2:-}"
      shift 2
      ;;
    --section)
      SECTION_FILTER="${2:-}"
      shift 2
      ;;
    --window-minutes)
      WINDOW_MINUTES="${2:-}"
      shift 2
      ;;
    --logging-provider)
      LOG_PROVIDER="${2:-ga}"
      shift 2
      ;;
    --logging-mode)
      LOG_MODE="${2:-gcloud}"
      shift 2
      ;;
    --metrics-only)
      METRICS_ONLY=true
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

if [[ "$METRICS_ONLY" = true ]]; then
  SECTION_FILTER="metrics_only"
fi

if [[ -n "${WINDOW_MINUTES}" ]]; then
  START_UTC="$(python3 - "$END_UTC" "$WINDOW_MINUTES" <<'PY'
from datetime import datetime, timedelta, timezone
import sys
end_utc = datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
minutes = int(sys.argv[2])
print((end_utc - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"
fi

if [ "$OUTPUT_MODE" = "json" ]; then
  OUTPUT_DIR="${OUTPUT_DIR:-audit_${SERVICE_NAME}_${START_UTC//:/-}_${END_UTC//:/-}}"
  mkdir -p "$OUTPUT_DIR"
  SUMMARY_FILE="$OUTPUT_DIR/summary.json"
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

run_with_timeout() {
  local timeout_seconds="$1"
  shift

  python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = float(sys.argv[1])
cmd = sys.argv[2:]

try:
    raise SystemExit(subprocess.run(cmd, check=False, timeout=timeout_seconds).returncode)
except subprocess.TimeoutExpired:
    print(f"Command timed out after {timeout_seconds:g}s: {' '.join(cmd)}", file=sys.stderr)
    raise SystemExit(124)
PY
}

count_json_items() {
  local file_path="$1"

  if [ ! -f "$file_path" ]; then
    echo 0
    return
  fi

  python3 - <<'PY' "$file_path"
import json, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    print(len(data) if isinstance(data, list) else 0)
except Exception:
    print(0)
PY
}

run_logging_query() {
  local query="$1"
  local output_file="${2:-}"
  local label="${3:-Logging query}"
  local limit="${4:-$LOG_LIMIT}"

  if [ "$DEBUG_MODE" = true ]; then
    log_section "$label (debug)"
    echo "timeout ${LOG_TIMEOUT_SECONDS}s ${LOG_MODE} logging read ..."
  fi

  case "$LOG_MODE" in
    gcloud)
      local cmd=(gcloud)
      case "$LOG_PROVIDER" in
        ga) cmd+=(logging read) ;;
        beta) cmd+=(beta logging read) ;;
        alpha) cmd+=(alpha logging read) ;;
        *)
          echo "Unknown logging provider: $LOG_PROVIDER" >&2
          return 1
          ;;
      esac
      cmd+=("$query" "--project=$PROJECT_ID" "--limit=$limit")
      if [ -n "$LOG_FRESHNESS" ]; then
        cmd+=("--freshness=$LOG_FRESHNESS")
      fi
      if [ "$OUTPUT_MODE" = "json" ]; then
        cmd+=("--format=json")
        run_with_timeout "$LOG_TIMEOUT_SECONDS" "${cmd[@]}" > "$output_file"
      else
        cmd+=("--format=table(timestamp,severity,resource.type,resource.labels.service_name,resource.labels.revision_name,textPayload,jsonPayload.message)")
        run_with_timeout "$LOG_TIMEOUT_SECONDS" "${cmd[@]}"
      fi
      ;;
    api)
      run_cloud_logging_api_query "$query" "$output_file" "$limit"
      ;;
    *)
      echo "Unknown logging mode: $LOG_MODE" >&2
      return 1
      ;;
  esac
}

run_cloud_logging_api_query() {
  local query="$1"
  local output_file="${2:-}"
  local limit="${3:-$LOG_LIMIT}"

  local access_token
  access_token="$(gcloud auth print-access-token)"

  run_with_timeout "$LOG_TIMEOUT_SECONDS" python3 - "$PROJECT_ID" "$query" "$START_UTC" "$END_UTC" "$limit" "$OUTPUT_MODE" "$output_file" "$access_token" <<'PY'
import json
import os
import sys
import urllib.parse
import urllib.request

project_id, query, start_utc, end_utc, limit, output_mode, output_file, access_token = sys.argv[1:9]
page_token = None
entries = []

base_filter = f'({query}) AND timestamp>="{start_utc}" AND timestamp<="{end_utc}"'

while True:
    params = {
        "resourceNames": f"projects/{project_id}",
        "filter": base_filter,
        "pageSize": str(limit),
        "orderBy": "timestamp desc",
    }
    if page_token:
        params["pageToken"] = page_token

    url = "https://logging.googleapis.com/v2/entries:list"
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    entries.extend(payload.get("entries", []))
    page_token = payload.get("nextPageToken")
    if not page_token or len(entries) >= int(limit):
        break

entries = entries[: int(limit)]

if output_mode == "json":
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, sort_keys=True)
else:
    for entry in entries:
        ts = entry.get("timestamp", "")
        severity = entry.get("severity", "")
        resource_type = entry.get("resource", {}).get("type", "")
        service_name = entry.get("resource", {}).get("labels", {}).get("service_name", "")
        revision_name = entry.get("resource", {}).get("labels", {}).get("revision_name", "")
        text_payload = entry.get("textPayload", "") or entry.get("jsonPayload", {}).get("message", "")
        print(f"{ts}\t{severity}\t{resource_type}\t{service_name}\t{revision_name}\t{text_payload}")
PY
}

run_metric_query() {
  local metric_type="$1"
  local value_field="$2"
  local output_file="${3:-}"
  local label="${4:-Cloud Run metric}"

  local filter_expr
  filter_expr="metric.type=\"${metric_type}\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\""

  local access_token
  access_token="$(gcloud auth print-access-token)"

  if [ "$DEBUG_MODE" = true ]; then
    log_section "$label (debug)"
    echo "timeout ${METRIC_TIMEOUT_SECONDS}s python3 metrics query ..."
  fi

  run_with_timeout "$METRIC_TIMEOUT_SECONDS" python3 - "$PROJECT_ID" "$metric_type" "$SERVICE_NAME" "$START_UTC" "$END_UTC" "$OUTPUT_MODE" "$value_field" "$output_file" "$access_token" <<'PY'
import json
import sys
import urllib.parse
import urllib.request

project_id, metric_type, service_name, start_utc, end_utc, output_mode, value_field, output_file, access_token = sys.argv[1:10]

params = {
    "filter": (
        f'metric.type="{metric_type}" '
        f'AND resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{service_name}"'
    ),
    "interval.startTime": start_utc,
    "interval.endTime": end_utc,
}
url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(
    url,
    headers={"Authorization": f"Bearer {access_token}"},
)

    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

series = payload.get("timeSeries", [])

if output_mode == "json":
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(series, fh, indent=2, sort_keys=True)
else:
    rows = []
    for ts in series:
        metric_labels = ts.get("metric", {}).get("labels", {})
        revision = ts.get("resource", {}).get("labels", {}).get("revision_name", "")
        for point in ts.get("points", []):
            value = point.get("value", {})
            rows.append({
                "startTime": point.get("interval", {}).get("endTime") or point.get("interval", {}).get("startTime", ""),
                "value": value.get("int64Value") or value.get("doubleValue") or value.get("stringValue") or "",
                "revision": revision,
                "response_code_class": metric_labels.get("response_code_class", ""),
            })

    for row in rows:
        print(f"{row['startTime']}\t{row['value']}\t{row['revision']}\t{row['response_code_class']}")
PY
}

log_section "Audit Window"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Window (UTC): $START_UTC -> $END_UTC"
echo "Window (Asia/Bangkok): 2026-06-21 01:10 -> 01:30"

should_run_section() {
  local section_name="$1"

  if [ -z "$SECTION_FILTER" ]; then
    return 0
  fi

  if [ "$SECTION_FILTER" = "metrics_only" ]; then
    case "$section_name" in
      "Cloud Run request logs"|"Budget webhook logs"|"Internal webhook / worker logs"|"Pub/Sub delivery logs"|"Cloud Scheduler logs"|"Cloud Tasks logs")
        return 1
        ;;
      *)
        return 0
        ;;
    esac
  fi

  case "$SECTION_FILTER" in
    request_logs)
      [ "$section_name" = "Cloud Run request logs" ]
      ;;
    budget_logs)
      [ "$section_name" = "Budget webhook logs" ]
      ;;
    internal_logs)
      [ "$section_name" = "Internal webhook / worker logs" ]
      ;;
    pubsub_logs)
      [ "$section_name" = "Pub/Sub delivery logs" ]
      ;;
    scheduler_logs)
      [ "$section_name" = "Cloud Scheduler logs" ]
      ;;
    cloud_tasks_logs)
      [ "$section_name" = "Cloud Tasks logs" ]
      ;;
    *)
      [ "$section_name" = "$SECTION_FILTER" ]
      ;;
  esac
}

if should_run_section "Cloud Run request logs"; then
  run_or_warn "Cloud Run request logs" run_logging_query \
    "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\"" \
    "${OUTPUT_DIR}/logs.json" \
    "Cloud Run request logs"
fi

if should_run_section "Budget webhook logs"; then
  run_or_warn "Budget webhook logs" run_logging_query \
    "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"BudgetAlert\" OR jsonPayload.message:\"BudgetAlert\" OR textPayload:\"/budget-alert\" OR jsonPayload.message:\"/budget-alert\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\"" \
    "${OUTPUT_DIR}/budget.json" \
    "Budget webhook logs"
fi

if should_run_section "Internal webhook / worker logs"; then
  run_or_warn "Internal webhook / worker logs" run_logging_query \
    "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload:\"internal\" OR jsonPayload.message:\"internal\" OR textPayload:\"webhook\" OR jsonPayload.message:\"webhook\" OR textPayload:\"worker\" OR jsonPayload.message:\"worker\") AND timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\"" \
    "${OUTPUT_DIR}/internal_webhook.json" \
    "Internal webhook / worker logs"
fi

if should_run_section "Pub/Sub delivery logs"; then
  run_or_warn "Pub/Sub delivery logs" run_logging_query \
    "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND ((resource.type=\"pubsub_subscription\" OR resource.type=\"pubsub_topic\" OR resource.type=\"pubsub_message\") OR protoPayload.serviceName=\"pubsub.googleapis.com\" OR textPayload:\"pubsub\" OR jsonPayload.message:\"pubsub\" OR textPayload:\"Pub/Sub\" OR jsonPayload.message:\"Pub/Sub\")" \
    "${OUTPUT_DIR}/pubsub.json" \
    "Pub/Sub delivery logs"
fi

if should_run_section "Cloud Scheduler logs"; then
  run_or_warn "Cloud Scheduler logs" run_logging_query \
    "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND ((resource.type=\"cloud_scheduler_job\" OR resource.type=\"audited_resource\" OR resource.type=\"service_account\") OR protoPayload.serviceName=\"cloudscheduler.googleapis.com\" OR textPayload:\"cloudscheduler\" OR jsonPayload.message:\"cloudscheduler\" OR textPayload:\"Cloud Scheduler\" OR jsonPayload.message:\"Cloud Scheduler\")" \
    "${OUTPUT_DIR}/scheduler.json" \
    "Cloud Scheduler logs"
fi

run_or_warn "Cloud Run request count" run_metric_query \
  "run.googleapis.com/request_count" \
  "int64Value" \
  "${OUTPUT_DIR}/metrics_request_count.json" \
  "Cloud Run request count"

run_or_warn "Cloud Run request latency" run_metric_query \
  "run.googleapis.com/request_latencies" \
  "doubleValue" \
  "${OUTPUT_DIR}/metrics_request_latencies.json" \
  "Cloud Run request latency"

run_or_warn "Cloud Run instance count" run_metric_query \
  "run.googleapis.com/container/instance_count" \
  "int64Value" \
  "${OUTPUT_DIR}/metrics_instance_count.json" \
  "Cloud Run instance count"

run_or_warn "Cloud Run memory utilization" run_metric_query \
  "run.googleapis.com/container/memory/utilizations" \
  "doubleValue" \
  "${OUTPUT_DIR}/metrics_memory_utilization.json" \
  "Cloud Run memory utilization"

run_or_warn "Cloud Run CPU utilization" run_metric_query \
  "run.googleapis.com/container/cpu/utilizations" \
  "doubleValue" \
  "${OUTPUT_DIR}/metrics_cpu_utilization.json" \
  "Cloud Run CPU utilization"

if should_run_section "Cloud Tasks logs"; then
  run_or_warn "Cloud Tasks logs" run_logging_query \
    "timestamp>=\"${START_UTC}\" AND timestamp<=\"${END_UTC}\" AND (resource.type=\"cloud_tasks_queue\" OR textPayload:\"cloudtasks\" OR jsonPayload.message:\"cloudtasks\")" \
    "${OUTPUT_DIR}/cloud_tasks.json" \
    "Cloud Tasks logs"
fi

if [ "$OUTPUT_MODE" = "json" ]; then
  log_section "JSON Output"
  echo "Wrote JSON files to: $OUTPUT_DIR"
  ls -1 "$OUTPUT_DIR"

  cat > "$SUMMARY_FILE" <<EOF
{
  "project": "${PROJECT_ID}",
  "service": "${SERVICE_NAME}",
  "window": {
    "start_utc": "${START_UTC}",
    "end_utc": "${END_UTC}"
  },
  "counts": {
    "logs": $(count_json_items "$OUTPUT_DIR/logs.json"),
    "budget": $(count_json_items "$OUTPUT_DIR/budget.json"),
    "internal_webhook": $(count_json_items "$OUTPUT_DIR/internal_webhook.json"),
    "pubsub": $(count_json_items "$OUTPUT_DIR/pubsub.json"),
    "scheduler": $(count_json_items "$OUTPUT_DIR/scheduler.json"),
    "metrics_request_count": $(count_json_items "$OUTPUT_DIR/metrics_request_count.json"),
    "metrics_request_latencies": $(count_json_items "$OUTPUT_DIR/metrics_request_latencies.json"),
    "metrics_instance_count": $(count_json_items "$OUTPUT_DIR/metrics_instance_count.json"),
    "metrics_memory_utilization": $(count_json_items "$OUTPUT_DIR/metrics_memory_utilization.json"),
    "metrics_cpu_utilization": $(count_json_items "$OUTPUT_DIR/metrics_cpu_utilization.json"),
    "cloud_tasks": $(count_json_items "$OUTPUT_DIR/cloud_tasks.json")
  }
}
EOF

  echo "summary.json"
fi

echo
echo "Audit complete."
