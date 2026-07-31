#!/bin/bash
# cleanup_artifact_registry.sh
# Deletes old Docker images in Google Artifact Registry, keeping only the N most recent images.
# This prevents storage costs from growing indefinitely due to continuous deployments.

set -e

PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-"asia-southeast1"}
REPO_NAME=${GCP_ARTIFACT_REPO:-"cloud-run-source-deploy"}
IMAGE_NAME=${IMAGE_NAME:-"fontokmai-api"}
KEEP_LATEST=${KEEP_LATEST_IMAGES:-2}

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set."
    exit 1
fi

IMAGE_PATH="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME"

echo "🔍 Checking images for: $IMAGE_PATH"
echo "📦 Keeping the latest $KEEP_LATEST images..."

# List images sorted by creation time (newest first: ~createTime)
# We only get the digests to avoid parsing complex text.
DIGESTS=$(gcloud artifacts docker images list "$IMAGE_PATH" \
  --sort-by="~createTime" \
  --format="value(version)")

if [ -z "$DIGESTS" ]; then
    echo "No images found in $IMAGE_PATH."
    exit 0
fi

# Convert string to array
DIGESTS_ARRAY=($DIGESTS)
TOTAL_IMAGES=${#DIGESTS_ARRAY[@]}

echo "📊 Total images found: $TOTAL_IMAGES"

if [ "$TOTAL_IMAGES" -le "$KEEP_LATEST" ]; then
    echo "✅ No old images to delete. Exiting."
    exit 0
fi

DELETE_COUNT=$((TOTAL_IMAGES - KEEP_LATEST))
echo "🗑️  Deleting $DELETE_COUNT old images..."

# Loop through and delete images older than the KEEP_LATEST count
for ((i=KEEP_LATEST; i<TOTAL_IMAGES; i++)); do
    DIGEST="${DIGESTS_ARRAY[$i]}"
    echo "Deleting image digest: $DIGEST..."
    # The --delete-tags flag ensures we don't leave dangling tags when deleting the digest
    gcloud artifacts docker images delete "$IMAGE_PATH@$DIGEST" --quiet --delete-tags
done

echo "🎉 Cleanup complete."
