#!/bin/bash
echo "Exporting GitLab variables..."
glab variable export --output json 2>/dev/null > gitlab_vars.json

echo "Extracting Secrets (Masked)..."
jq -r '.[] | select(.masked == true) | "\(.key)=\(.value)"' gitlab_vars.json > secrets.env

echo "Extracting Variables (Unmasked)..."
jq -r '.[] | select(.masked == false) | "\(.key)=\(.value)"' gitlab_vars.json > vars.env

echo "Importing to GitHub Secrets..."
env -u GITHUB_TOKEN gh secret set -f secrets.env

echo "Importing to GitHub Variables..."
env -u GITHUB_TOKEN gh variable set -f vars.env

echo "Cleaning up..."
rm gitlab_vars.json secrets.env vars.env migrate_vars.sh
echo "Done!"
