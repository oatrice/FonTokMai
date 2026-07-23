#!/usr/bin/env bash
set -e

echo "🚀 Starting FonMaYang Full-Stack (Frontend + Backend) Integration Test..."

# Ensure Python virtual environment with Playwright is available
PYTHON_BIN="/tmp/pw_env/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Run Full-Stack Playwright Integration Test
$PYTHON_BIN ./tests/e2e/test_fullstack_integration.py

echo "✅ Full-Stack Integration Test Completed Successfully!"
