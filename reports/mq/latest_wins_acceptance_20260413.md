# MQ Latest-Wins 验收报告（2026-04-13）

## 1. 目标与结论

本次验收目标是把 `docs/07_MESSAGE_QUEUE_DESIGN.md` 的“零点二 latest-wins”方案落到可运行代码，并验证：

1. 小红书短时多条消息最终只保留一条可见 AI 回复。
2. 旧候选回复在 sender 侧可被 stale gate 丢弃。
3. 业务状态提交后置到最终获胜轮次，旧轮次不提交。
4. `last_ack_seq` 作为确认游标正确推进，不再误用 `last_consumed_seq`。

验收结论：`PASS`（代码、集成测试、主链路回归全部通过）。

## 2. 关键实现项

1. 新增 turn 级草稿与延迟提交链路：
   - `src/services/queue/turn_draft_models.py`
   - `src/services/queue/turn_sandbox.py`
   - `src/services/queue/turn_commit_service.py`
2. `UserService` 增加 turn sandbox（contextvars），将轮次内状态写入暂存区，提交阶段再落地。
3. `QueueStore` 增加并落地 latest-wins 关键字段与流程：
   - `conversation_key / profile_key / last_ack_seq / pending_turn_id / covered_end_seq`
   - stale 判断、stale drop、finalize commit、committed turn 幂等。
4. `MessageOrchestrator`、`ReplySenderWorker` 改造为“生成候选 -> stale 复核 -> 发送 -> 提交 -> ack 推进”。
5. 补充 silent 分支提交前二次 stale 复核，避免 silent 轮次被覆盖后仍提交。
6. 修复 ack 游标语义：
   - 仅在缺失 `last_ack_seq` 的历史会话回退到 `last_consumed_seq`；
   - 不再把 `last_ack_seq=0` 误判为需要回退，避免 outbox 被全量误判 stale。
7. 显式暴露 latest-wins 关键配置：
   - `MQ_FORCE_FLUSH_ENABLED`
   - `MQ_PRE_SEND_SILENCE_MS`
8. 将 `MQ_FORCE_FLUSH_ENABLED` 默认值切换为 `false`（生产默认关闭），并补充开关生效单测。

## 3. 验收测试

执行命令：

```bash
pytest -q -o addopts='' tests/integration/test_message_queue_latest_wins_commit_integration.py tests/integration/test_message_queue_pipeline_integration.py tests/integration/test_xhs_ingest_to_delivery_local_http.py
pytest -q -o addopts='' tests/unit/test_queue_store.py tests/unit/test_message_orchestrator.py tests/unit/test_reply_sender_worker.py tests/unit/test_message_queue_worker.py
pytest -q -o addopts='' tests/unit/test_message_orchestrator.py tests/unit/test_queue_intent_classifier.py
pytest -q -o addopts='' tests/unit/test_process_chat_turn_use_case.py tests/unit/test_process_chat_turn_async_backfill.py tests/unit/test_chat_service_regressions.py
pytest -q -o addopts='' tests/unit/test_app_mq_toggle.py tests/unit/test_xiaohongshu_ingest_route.py tests/unit/test_reply_delivery_service.py tests/unit/test_queue_intent_classifier.py
```

结果摘要：

1. latest-wins 集成验收：`8 passed`
2. MQ 核心单测回归：`29 passed`
3. orchestrator 配置闸门回归：`18 passed`（含 force_flush 开关与 pre-send silence 开关测试）
4. chat 主链路回归：`448 passed`（`11 warnings`，为既有 AsyncMock 未 await 警告，非本次改动引入）
5. MQ 路由/开关/投递回归：`10 passed`（含 app startup toggle、ingest route、delivery fallback、intent classifier）

## 4. 新增/更新测试点

1. `tests/integration/test_message_queue_latest_wins_commit_integration.py`
   - `test_latest_wins_sender_only_delivers_and_commits_last_turn`
   - `test_silent_branch_rechecks_stale_before_commit`
2. 口径同步更新：
   - `tests/integration/test_message_queue_pipeline_integration.py`
   - `tests/integration/test_xhs_ingest_to_delivery_local_http.py`

## 5. 风险与后续建议

1. 当前 latest-wins 采用“`last_ack_seq` 窗口重覆盖”策略，未确认消息会在后续获胜轮次中重覆盖生成，符合单条最终回复目标。
2. 建议后续增加真实外部 `XHS_REPLY_API` 的生产 smoke 周期性报告，持续监控：
   - `stale_drop_count`
   - `outbox_delivery_success / outbox_delivery_drop`
   - `pending_depth`
