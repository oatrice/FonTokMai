#!/usr/bin/env bash
set -e

echo "🚀 Starting FonMaYang Newman API Integration Tests..."

# Ensure results directory exists
mkdir -p results

# Check if newman is installed, install locally if missing
if ! command -v newman &> /dev/null; then
    echo "📦 Installing Newman test runner..."
    npx -y newman --version || npm install -g newman newman-reporter-htmlextra
fi

# Determine Base URL
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "🌐 Target Base URL: $BASE_URL"

# Run Newman Collection
npx -y newman run ./tests/integration/newman/collections/fonmayang-api-tests.json \
  -e ./tests/integration/newman/environments/local-dev.json \
  --env-var "BASE_URL=$BASE_URL" \
  -r cli,junit,htmlextra \
  --reporter-junit-export ./results/newman-junit.xml \
  --reporter-htmlextra-export ./results/newman-report.html \
  --reporter-htmlextra-title "FonMaYang API Integration Test Report"

echo "✅ Newman API Integration Tests Completed Successfully!"
echo "📄 Report HTML: ./results/newman-report.html"
echo "📊 Report JUnit: ./results/newman-junit.xml"
