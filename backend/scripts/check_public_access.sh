#!/bin/bash
# =============================================================================
# check_public_access.sh
# -----------------------------------------------------------------------------
# Audits the public-access IAM status of Cloud Run services.
# Checks whether allUsers → roles/run.invoker is bound on each service.
# Compatible with bash 3.2+ (macOS default).
#
# Usage:
#   ./check_public_access.sh [OPTIONS]
#
# Options:
#   --project  <id>      Override GCP project ID
#   --region   <region>  Override GCP region (default: asia-southeast1)
#   --service  <name>    Check a single service instead of all services
#   --expect   public|private
#                        Exit non-zero if any service doesn't match expected state
#   --quiet              Suppress all output except errors (useful for CI)
#   --help               Show this help message
# =============================================================================
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env (try backend root first, then parent)
for env_file in "$SCRIPT_DIR/../.env" "$SCRIPT_DIR/../../.env"; do
  if [ -f "$env_file" ]; then
    set -a; source "$env_file"; set +a
    break
  fi
done

PROJECT_ID="${GCP_PROJECT_ID:-${GCP_PROJECT:-fonmayang}}"
REGION="${GCP_LOCATION:-asia-southeast1}"
SINGLE_SERVICE=""
EXPECT_STATE=""   # "public" | "private" | ""
QUIET=false

# ── Argument Parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  PROJECT_ID="$2"; shift 2 ;;
    --region)   REGION="$2";     shift 2 ;;
    --service)  SINGLE_SERVICE="$2"; shift 2 ;;
    --expect)   EXPECT_STATE="$2"; shift 2 ;;
    --quiet)    QUIET=true; shift ;;
    --help)
      sed -n '/^# Usage:/,/^# =/p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "❌ Unknown option: $1"; exit 1 ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { $QUIET || echo "$@"; }

check_deps() {
  for cmd in gcloud jq; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "❌ Required tool not found: $cmd"
      exit 1
    fi
  done
}

# Returns "PUBLIC" if allUsers invoker binding exists, else "PRIVATE"
get_access_status() {
  local service="$1"
  local policy
  policy=$(gcloud run services get-iam-policy "$service" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format=json 2>/dev/null) || { echo "ERROR"; return; }

  local has_public
  has_public=$(echo "$policy" | jq -r '
    [ .bindings // [] |
      .[] |
      select(.role == "roles/run.invoker") |
      .members[] |
      select(. == "allUsers")
    ] | length
  ' 2>/dev/null || echo "0")

  if [ "${has_public:-0}" -gt 0 ]; then
    echo "PUBLIC"
  else
    echo "PRIVATE"
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
check_deps

log ""
log "╔══════════════════════════════════════════════════════════╗"
log "║       🔍  Cloud Run Public Access Audit                  ║"
log "╠══════════════════════════════════════════════════════════╣"
log "║  Project : $PROJECT_ID"
log "║  Region  : $REGION"
log "╚══════════════════════════════════════════════════════════╝"
log ""

# ── Collect services to check ─────────────────────────────────────────────────
SERVICES_FILE="$(mktemp)"
trap 'rm -f "$SERVICES_FILE"' EXIT

if [[ -n "$SINGLE_SERVICE" ]]; then
  echo "$SINGLE_SERVICE" > "$SERVICES_FILE"
else
  log "📋 Fetching list of Cloud Run services..."
  gcloud run services list \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format="value(metadata.name)" 2>/dev/null > "$SERVICES_FILE" || true

  if [ ! -s "$SERVICES_FILE" ]; then
    log "⚠️  No Cloud Run services found in project '$PROJECT_ID' (region: $REGION)."
    exit 0
  fi
fi

SERVICE_COUNT=$(wc -l < "$SERVICES_FILE" | tr -d ' ')
log "Checking $SERVICE_COUNT service(s)..."
log ""

# ── Audit loop ────────────────────────────────────────────────────────────────
PUBLIC_COUNT=0
PRIVATE_COUNT=0
ERROR_COUNT=0
MISMATCH_COUNT=0

while IFS= read -r svc || [[ -n "$svc" ]]; do
  [ -z "$svc" ] && continue

  STATUS=$(get_access_status "$svc")

  case "$STATUS" in
    PUBLIC)
      icon="🌐"
      label="PUBLIC  "
      PUBLIC_COUNT=$((PUBLIC_COUNT + 1))
      ;;
    PRIVATE)
      icon="🔒"
      label="PRIVATE "
      PRIVATE_COUNT=$((PRIVATE_COUNT + 1))
      ;;
    ERROR)
      icon="❓"
      label="ERROR   "
      ERROR_COUNT=$((ERROR_COUNT + 1))
      ;;
  esac

  # Check against expected state
  MISMATCH_FLAG=""
  if [[ -n "$EXPECT_STATE" ]]; then
    UPPER_EXPECT=$(echo "$EXPECT_STATE" | tr '[:lower:]' '[:upper:]')
    if [[ "$STATUS" != "$UPPER_EXPECT" && "$STATUS" != "ERROR" ]]; then
      MISMATCH_COUNT=$((MISMATCH_COUNT + 1))
      MISMATCH_FLAG="  ⚠️  UNEXPECTED (expected: $EXPECT_STATE)"
    fi
  fi

  log "  ${icon}  ${label}  ${svc}${MISMATCH_FLAG}"

done < "$SERVICES_FILE"

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "──────────────────────────────────────────────────────────"
log "📊 Summary"
log "──────────────────────────────────────────────────────────"
log "  🌐  Public  : $PUBLIC_COUNT"
log "  🔒  Private : $PRIVATE_COUNT"
[ "$ERROR_COUNT" -gt 0 ]    && log "  ❓  Errors  : $ERROR_COUNT"
[ "$MISMATCH_COUNT" -gt 0 ] && log "  ⚠️   Mismatches: $MISMATCH_COUNT"
log ""

# ── Exit code based on --expect ───────────────────────────────────────────────
if [[ -n "$EXPECT_STATE" && "$MISMATCH_COUNT" -gt 0 ]]; then
  log "❌ Audit FAILED: $MISMATCH_COUNT service(s) have unexpected access state."
  exit 1
fi

if [[ "$ERROR_COUNT" -gt 0 ]]; then
  log "⚠️  Audit completed with $ERROR_COUNT error(s) (could not read IAM policy)."
  exit 2
fi

log "✅ Audit complete."
