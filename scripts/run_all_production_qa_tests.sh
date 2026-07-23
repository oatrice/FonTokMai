#!/usr/bin/env bash
set -e

echo "=========================================================================="
echo "🚀 FonMaYang Complete 6-Suite Production QA & Full-Stack E2E Test Runner"
echo "=========================================================================="

PYTHON_BIN="/tmp/pw_env/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

mkdir -p scratch/qa_reports

echo ""
echo "--- [1/6] Live Runway Engine & Emergency Overdrive ---"
$PYTHON_BIN ./tests/e2e/test_suite_1_runway_overdrive.py

echo ""
echo "--- [2/6] Transparent Budget Jars Allocation ---"
$PYTHON_BIN ./tests/e2e/test_suite_2_budget_jars.py

echo ""
echo "--- [3/6] Dynamic Circuit Breaker & API Resiliency Fallback ---"
$PYTHON_BIN ./tests/e2e/test_suite_3_circuit_breaker.py

echo ""
echo "--- [4/6] Zero-PII Stripe Webhook -> Dashboard Auto-Update ---"
$PYTHON_BIN ./tests/e2e/test_suite_4_stripe_auto_refresh.py

echo ""
echo "--- [5/6] Serverless Webhook Latency & Cloud Tasks ---"
$PYTHON_BIN ./tests/e2e/test_suite_5_serverless_webhooks.py

echo ""
echo "--- [6/6] Light/Dark Mode Theme Toggle & Accessibility ---"
$PYTHON_BIN ./tests/e2e/test_suite_6_theme_a11y.py

echo ""
echo "=========================================================================="
echo "🎉 ALL 6 PRODUCTION QA & E2E TEST SUITES PASSED 100% SUCCESS!"
echo "📸 Visual Screenshots Saved to: ./scratch/qa_reports/"
echo "=========================================================================="
