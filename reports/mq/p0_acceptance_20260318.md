# P0 Acceptance Report

- Date: 2026-03-18
- Commit: working tree (uncommitted)
- Executor: Codex (GPT-5)
- Environment: local dev, Python 3, Redis optional

## Scope Progress

- [x] ingest API route (`/api/xiaohongshu/messages/ingest`)
- [x] queue store (session/seq/msg/ready/outbox/dedupe/lock)
- [x] orchestrator ingest + run_user_turn
- [x] generation stale drop
- [x] outbox sender retry worker
- [x] queue_full backpressure (Lua atomic)
- [x] pending_depth metric exposure (`/api/doubao/stats.statistics.message_queue.pending_depth`)
- [x] stale RUNNING recovery with per-loop limit (`MQ_RECOVERY_BATCH_SIZE`)
- [x] fail_streak circuit-breaker retry delay
- [x] timestamp parse tolerance + invalid timestamp metric
- [x] local pipeline integration E2E（无外部依赖）
- [x] local HTTP delivery E2E（真实 HTTP 请求，本地回调接收）
- [ ] full E2E with real xiaohongshu production endpoint

## Test Commands

```bash
python3 -m compileall src/services/queue src/workers src/api/routes/xiaohongshu_ingest.py src/api/app.py src/api/routes/system.py
pytest -q -o addopts='' tests/unit/test_queue_intent_classifier.py tests/unit/test_queue_store.py tests/unit/test_message_orchestrator.py tests/unit/test_reply_sender_worker.py tests/unit/test_message_queue_worker.py tests/unit/test_reply_delivery_service.py
pytest -q -o addopts='' tests/integration/test_message_queue_pipeline_integration.py
# local port bind required
pytest -q -o addopts='' tests/integration/test_xhs_ingest_to_delivery_local_http.py
# production endpoint smoke (requires XHS_REPLY_API)
python3 scripts/run_mq_p0_production_smoke.py --timeout-seconds 30 --report-file reports/mq/p0_production_smoke_<ts>.md
pytest -q -o addopts='' tests/unit/test_real_ai_regression_runner.py tests/unit/test_conversation_ending_service.py
```

## Results Summary

- compileall: PASS
- queue unit tests: PASS
- queue integration tests: 4 passed
- regression-related existing tests: 45 passed
- combined verification: 68 passed + local-http e2e 1 passed

## Risks / Open Items

1. Real xiaohongshu production endpoint (`XHS_REPLY_API`) not verified in this run.
2. 已提供生产联调脚本 `scripts/run_mq_p0_production_smoke.py`，待在线上环境执行。

## Verdict

- [ ] PASS (P0 fully done)
- [x] PARTIAL (P0 in progress, code-ready pending real endpoint E2E)
