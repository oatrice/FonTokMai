#!/bin/bash

# ==============================================================================
# FonMaYang - EMSC Worker Free Tier VM Provisioning Script
# This script provisions an e2-micro Google Compute Engine instance in the US
# (qualifies for free tier) to run the standalone EMSC WebSocket worker.
# ==============================================================================

set -e

# Default variables
PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
ZONE="us-west1-a"
INSTANCE_NAME="emsc-worker-vm"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"

echo "=================================================="
echo "🚀 Provisioning EMSC Worker VM ($INSTANCE_NAME)"
echo "=================================================="

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID is not set and no default gcloud project found."
    exit 1
fi

echo "Project ID: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Machine Type: $MACHINE_TYPE (Free Tier eligible in us-west1)"

# Check if instance already exists
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "⚠️ Instance $INSTANCE_NAME already exists! Skipping creation."
else
    echo "🔄 Creating VM instance..."
    # Create the instance with OS Login enabled and a startup script to install dependencies
    gcloud compute instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --image-family=$IMAGE_FAMILY \
        --image-project=$IMAGE_PROJECT \
        --boot-disk-size=10GB \
        --boot-disk-type=pd-standard \
        --tags=emsc-worker \
        --metadata=enable-oslogin=TRUE,startup-script='#!/bin/bash
echo "Starting initial VM setup..."
apt-get update
apt-get install -y git python3-venv python3-pip
# Ensure the deployment directory exists
mkdir -p /opt/fonmayang/emsc_worker
chown -R root:root /opt/fonmayang
echo "Setup complete."
'
    echo "✅ VM $INSTANCE_NAME created successfully."
fi

echo "=================================================="
echo "🎉 Provisioning complete!"
echo "Next Steps:"
echo "1. The GitLab CI pipeline will now be able to deploy the worker code via SSH."
echo "2. Ensure your GitLab CI Service Account has 'Compute OS Login' and 'Compute Instance Admin' roles."
echo "=================================================="
