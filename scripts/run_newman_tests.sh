#!/usr/bin/env bash
set -e

echo "🚀 Starting FonMaYang Newman API Integration Tests..."

# Ensure results directory exists
mkdir -p results

# Determine Base URL
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "🌐 Target Base URL: $BASE_URL"

# Run Newman Collection with HTML Extra reporter
npx -y --package=newman --package=newman-reporter-htmlextra \
  newman run ./tests/integration/newman/collections/fonmayang-api-tests.json \
  -e ./tests/integration/newman/environments/local-dev.json \
  --env-var "BASE_URL=$BASE_URL" \
  -r cli,junit,htmlextra \
  --reporter-junit-export ./results/newman-junit.xml \
  --reporter-htmlextra-export ./results/newman-report.html \
  --reporter-htmlextra-title "FonMaYang API Integration Test Report"

echo "✅ Newman API Integration Tests Completed Successfully!"
echo "📄 Report HTML: ./results/newman-report.html"
echo "📊 Report JUnit: ./results/newman-junit.xml"
