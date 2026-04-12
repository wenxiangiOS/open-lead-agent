# Message Queue Runbook

更新时间：2026-04-13

## 1. Redis 故障应急

### 现象
- `/api/xiaohongshu/messages/ingest` 成功率下降
- `/api/doubao/stats` 中 `message_queue.pending_depth` 不更新或异常
- worker 日志出现 Redis 连接失败

### 处置
1. 确认 Redis 进程与网络连通。
2. 检查 `REDIS_*` 配置、密码和 DB。
3. 重启应用实例，观察 `mq.worker`、`mq.sender` 是否恢复。
4. 如 Redis 不可用，临时开启回退链路 `/api/doubao/chat`。
5. 关注恢复后积压是否下降：`pending_depth`、`outbox_ready`。

### 验收
- `pending_depth` 恢复变化
- `ingest_accepted` 与 `turn_succeeded` 持续增长

## 2. 发送持续失败应急

### 现象
- `outbox_delivery_retry` 持续增长
- `outbox_delivery_success` 低
- `outbox_delivery_drop` 出现上升

### 处置
1. 检查 `XHS_REPLY_API` 可达性、认证与限流。
2. 检查下游响应码与错误体（sender 日志）。
3. 确认幂等键 `clientMsgId=job_id` 已透传。
4. 临时提高 `MQ_OUTBOX_MAX_RETRIES`（短期）并观察。
5. 若下游大面积故障，先暂停外发通道，保留 outbox，待恢复后继续发送。

### 验收
- `outbox_delivery_success / outbox_created` 回升
- `outbox_ready` 开始下降

## 3. 队列积压应急

### 现象
- `pending_depth` 高位不降
- `ingest_queue_full` 增长
- 用户侧响应延迟变大

### 处置
1. 确认 worker 在运行：`mq.worker started`。
2. 检查 `turn_failed`、`turn_stale` 是否异常高。
3. 调整处理参数：
   - 降低 `MQ_DEBOUNCE_MS` / `MQ_DEBOUNCE_APPEND_MS`
   - 增大 `MQ_READY_BATCH_SIZE`
   - 视情况增加实例
4. 若单用户故障热点明显，检查 `fail_streak` 熔断是否生效。
5. 保持 `MQ_MAX_PENDING_MESSAGES` 背压，避免无界增长。

### 验收
- `pending_depth` 拐头下降
- `ingest_queue_full` 增速下降

## 4. 常用观测指标

在 `/api/doubao/stats` -> `statistics.message_queue`：

- 队列：`pending_depth`, `ready_users`, `outbox_ready`
- 入站漏斗：`ingest_total`, `ingest_accepted`, `ingest_duplicate`, `ingest_queue_full`
- 执行漏斗：`turn_started`, `turn_succeeded`, `turn_failed`, `turn_stale`
- 空回复：`empty_response_business_silent`, `empty_response_error`
- 联系方式校验：`contact_validation_retry`, `contact_validation_silent`
- 发送漏斗：`outbox_created`, `outbox_delivery_success`, `outbox_delivery_retry`, `outbox_delivery_drop`
- 质量：`invalid_timestamp_count`, `stale_drop_count`

## 5. 发布后首日检查清单

1. 连发消息（5 条）不丢不乱序。
2. 处理中 cancel 后旧回复不下发。
3. 重复 `platformMsgId` 仅处理一次。
4. 发送失败可重试，重试后可恢复。
5. 背压命中时返回 `queue_full`，系统无雪崩。
6. 小红书 latest-wins 参数核对：
   - `MQ_FORCE_FLUSH_ENABLED=false`（生产默认关闭）
   - `MQ_PRE_SEND_SILENCE_MS=400`（可按体验在 300~800 之间调优）


## 6. 生产联调 Smoke

在配置真实外发地址后执行：

```bash
export XHS_REPLY_API='https://<your-xhs-endpoint>'
python3 scripts/run_mq_p0_production_smoke.py --timeout-seconds 30 --report-file reports/mq/p0_production_smoke_$(date +%Y%m%d_%H%M%S).md
```

判定标准：输出 `[PASS] production smoke finished`，且 metrics 中 `outbox_delivery_success >= 1`。

脚本会生成报告文件（`--report-file`），可直接作为 P0 最终联调证据。


## 7. 关键环境变量

- 核心开关：`MQ_ENABLED`
- 外发通道：`XHS_REPLY_API`, `XHS_REPLY_API_BACKUP`, `XHS_REPLY_TIMEOUT_SECONDS`
- 聚合参数：`MQ_DEBOUNCE_MS`, `MQ_DEBOUNCE_APPEND_MS`, `MQ_DEBOUNCE_MAX_MS`
- latest-wins 参数：`MQ_FORCE_FLUSH_ENABLED`（建议 false）, `MQ_PRE_SEND_SILENCE_MS`
- 执行参数：`MQ_READY_BATCH_SIZE`, `MQ_WORKER_POLL_MS`, `MQ_RUNNING_RECHECK_MS`
- 重试参数：`MQ_OUTBOX_MAX_RETRIES`, `MQ_SENDER_POLL_MS`
- 背压：`MQ_MAX_PENDING_MESSAGES`
- 熔断：`MQ_FAIL_STREAK_THRESHOLD`, `MQ_FAIL_STREAK_COOLDOWN_MS`
- P2 参数：`MQ_PRIORITY_BOOST_MS`, `MQ_ADAPTIVE_DEBOUNCE_ENABLED`, `MQ_HOT_USER_PENDING_THRESHOLD`, `MQ_HOT_USER_QUOTA_PER_LOOP`, `MQ_CONTEXT_COMPACTION_ENABLED`


## 8. P0 状态自动收口

当生产 smoke 报告为 PASS 时，可自动将 `docs/message_queue_status.yaml` 的 `p0.state` 改为 `DONE`：

```bash
python3 scripts/finalize_p0_from_smoke_report.py \
  --report reports/mq/p0_production_smoke_<ts>.md \
  --status docs/message_queue_status.yaml
```
