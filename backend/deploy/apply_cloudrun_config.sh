#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/cloudrun.env" ]; then
  # shellcheck disable=SC1091
  set -a
  source "$SCRIPT_DIR/cloudrun.env"
  set +a
fi

: "${CLOUD_RUN_SERVICE:=fontokmai-api}"
: "${CLOUD_RUN_REGION:=asia-southeast1}"
: "${CLOUD_RUN_SERVICE_ACCOUNT:=cloud-run-runtime@fonmayang.iam.gserviceaccount.com}"
: "${CLOUD_RUN_ALLOW_UNAUTHENTICATED:=true}"
: "${CLOUD_RUN_MEMORY:=1Gi}"
: "${CLOUD_RUN_CPU:=1}"
: "${CLOUD_RUN_TIMEOUT:=300}"
: "${CLOUD_RUN_MIN_INSTANCES:=1}"
: "${CLOUD_RUN_MAX_INSTANCES:=2}"
: "${CLOUD_RUN_CONCURRENCY:=40}"
: "${CLOUD_RUN_CPU_BOOST:=true}"
: "${CLOUD_RUN_NO_CPU_THROTTLING:=true}"

echo "Applying Cloud Run config for ${CLOUD_RUN_SERVICE}"

CPU_BOOST_FLAG="--cpu-boost"
if [ "$CLOUD_RUN_CPU_BOOST" != "true" ]; then
  CPU_BOOST_FLAG="--no-cpu-boost"
fi

CPU_THROTTLING_FLAG="--no-cpu-throttling"
if [ "$CLOUD_RUN_NO_CPU_THROTTLING" != "true" ]; then
  CPU_THROTTLING_FLAG="--cpu-throttling"
fi

gcloud run services update "$CLOUD_RUN_SERVICE" \
  --region "$CLOUD_RUN_REGION" \
  --service-account="$CLOUD_RUN_SERVICE_ACCOUNT" \
  --memory "$CLOUD_RUN_MEMORY" \
  --cpu "$CLOUD_RUN_CPU" \
  --timeout "$CLOUD_RUN_TIMEOUT" \
  --min-instances "$CLOUD_RUN_MIN_INSTANCES" \
  --max-instances "$CLOUD_RUN_MAX_INSTANCES" \
  --concurrency "$CLOUD_RUN_CONCURRENCY" \
  $CPU_BOOST_FLAG \
  $CPU_THROTTLING_FLAG

if [ "$CLOUD_RUN_ALLOW_UNAUTHENTICATED" = "true" ]; then
  gcloud run services add-iam-policy-binding "$CLOUD_RUN_SERVICE" \
    --region "$CLOUD_RUN_REGION" \
    --member="allUsers" \
    --role="roles/run.invoker"
else
  gcloud run services remove-iam-policy-binding "$CLOUD_RUN_SERVICE" \
    --region "$CLOUD_RUN_REGION" \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet || true
fi
