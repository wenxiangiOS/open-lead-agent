#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source ".env" >/dev/null 2>&1 || true
fi

if [[ -z "${ARK_API_KEY:-}" ]]; then
  echo "ARK_API_KEY is not set. Please configure it in .env or environment variables."
  exit 1
fi

TEST_FILE="tests/integration/test_profile_collection_policy_integration.py"

if [[ $# -gt 0 ]]; then
  pytest "$TEST_FILE" -q -k "$1"
else
  pytest "$TEST_FILE" -q
fi
