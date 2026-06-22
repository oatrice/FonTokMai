#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "backend/venv is missing. Create it first:"
  echo "  cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ $# -gt 0 ]]; then
  ARGS=()
  for arg in "$@"; do
    if [[ "$arg" == backend/* ]]; then
      ARGS+=("${arg#backend/}")
    else
      ARGS+=("$arg")
    fi
  done
else
  ARGS=(tests/)
fi

exec "$PYTHON_BIN" -m pytest "${ARGS[@]}"
