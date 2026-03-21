#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
MQ_ACCOUNTS="${MQ_ACCOUNTS:-20}"
MQ_MESSAGES_PER_ACCOUNT="${MQ_MESSAGES_PER_ACCOUNT:-10}"
MQ_CONCURRENCY="${MQ_CONCURRENCY:-20}"

echo "[preflight] 1/4 quality upper bound gate"
bash scripts/run_quality_upper_bound_gate.sh

echo "[preflight] 2/4 mq ingest regression"
python3 scripts/run_mq_ingest_regression.py --base-url "$BASE_URL"

echo "[preflight] 3/4 mq load gate"
python3 scripts/run_mq_load_test.py \
  --base-url "$BASE_URL" \
  --accounts "$MQ_ACCOUNTS" \
  --messages-per-account "$MQ_MESSAGES_PER_ACCOUNT" \
  --concurrency "$MQ_CONCURRENCY" \
  --include-dashboard \
  --gate

echo "[preflight] 4/4 refresh report index"
python3 scripts/generate_report_index.py

echo "[preflight] PASS"
echo "[preflight] report index: reports/INDEX.md"
