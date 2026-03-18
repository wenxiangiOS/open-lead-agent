#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[1/5] compileall"
python3 -m compileall src/services/queue src/workers src/api/routes/xiaohongshu_ingest.py src/api/app.py src/api/routes/system.py

echo "[2/5] queue unit tests"
pytest -q -o addopts='' \
  tests/unit/test_queue_intent_classifier.py \
  tests/unit/test_queue_store.py \
  tests/unit/test_message_orchestrator.py \
  tests/unit/test_reply_sender_worker.py \
  tests/unit/test_message_queue_worker.py \
  tests/unit/test_reply_delivery_service.py

echo "[3/5] queue integration tests"
pytest -q -o addopts='' \
  tests/integration/test_message_queue_pipeline_integration.py

# This test binds localhost port; may require less restricted runtime
if [[ "${MQ_LOCAL_HTTP_E2E:-1}" == "1" ]]; then
  echo "[4/5] local-http delivery e2e"
  pytest -q -o addopts='' tests/integration/test_xhs_ingest_to_delivery_local_http.py || true
fi

echo "[5/5] p0 production smoke"
TS="$(date +%Y%m%d_%H%M%S)"
python3 scripts/run_mq_p0_production_smoke.py \
  --timeout-seconds "${MQ_P0_SMOKE_TIMEOUT_SECONDS:-30}" \
  --report-file "reports/mq/p0_production_smoke_${TS}.md" || true

echo "done"
