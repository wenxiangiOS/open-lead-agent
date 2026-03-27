# 多次发送消息处理方案设计文档

> 创建时间：2026-03-06
> 最后更新：2026-03-19
> 状态：建议按本方案实施
> 文档类型：正式技术方案

## 执行入口（只记这一个文档）

后续无论是你本人还是其他模型协作，**只需要先打开本文件**，然后按下面 3 个入口执行：

1. 实现标准：当前文档的 `零、2026-03-18 最终实施基线`
2. 当前进度：`docs/message_queue_status.yaml`
3. 验收证据：`reports/mq/p0_acceptance_*.md`

协作口令（可直接复制给其他模型）：

`先按 docs/07_MESSAGE_QUEUE_DESIGN.md 的“执行入口”和“零”章节实施，再更新 docs/message_queue_status.yaml，并提交 reports/mq/p0_acceptance_*.md。`

## 实施状态看板（跨模型协作必读）

> 权威状态文件：`docs/message_queue_status.yaml`
> 验收证据目录：`reports/mq/`

当前状态（人工摘要）：

- P0：`DONE`（代码、本地 E2E、108 场景回归已收口）
- P1：`DONE`（六项优化已完成并提供验收报告）
- P2：`DONE`（六项优化已完成并提供验收报告）
- 最近更新时间：`2026-03-18 23:59:30 +0800`
- 基线 commit：`2bef0da`

协作规则：

1. 任何模型完成 P0/P1/P2 后，必须同步更新 `docs/message_queue_status.yaml`。
2. 状态从 `NOT_DONE` 改为 `DONE` 前，必须先补齐 `reports/mq/*acceptance*.md` 验收证据。
3. 若代码与状态文件冲突，以“测试与验收报告”作为最终判定依据。

## 协作实施总览（给其他模型的单页交接）

> 目标：让任何模型在 2 分钟内知道“哪些已完成、哪些未完成、下一步做什么”。

### A. 已完成（截至 2026-03-18）

1. Queue 核心模块与 Worker 已实现并接入应用启动：
   - `src/services/queue/*`
   - `src/workers/message_queue_worker.py`
   - `src/workers/reply_sender_worker.py`
2. 入站接口已实现：`POST /api/xiaohongshu/messages/ingest`
3. 状态/指标面板已实现：`/api/doubao/mq/dashboard`
4. P1、P2 状态为 `DONE`，并有验收报告：
   - `reports/mq/p1_acceptance_20260318.md`
   - `reports/mq/p2_acceptance_20260318.md`
5. P0 本地链路测试已通过（含本地 HTTP E2E）：
   - `reports/mq/p0_acceptance_20260318.md`
6. 测试页已切换到真链路模式：
   - 入站：`POST /api/xiaohongshu/messages/ingest`
   - 回执：`GET /api/xiaohongshu/messages/replies`

### B. 未完成（可选增强）

1. 真实外部发送端点 `XHS_REPLY_API` 生产端到端 smoke 报告可持续补充。
2. 外部调用方（如 3chat.ai）是否已全量切换到 `ingest` 建议在仓库外补闭环记录。

### C. 下一步执行顺序（回归口径）

1. Chat 场景回归（默认自动排除 `mq`）：`python3 scripts/run_real_ai_regression.py`
2. MQ ingest 回归（真实接口口径）：`python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000`
3. 若需一键串行执行：`python3 scripts/run_real_ai_regression.py --include-mq --mq-base-url http://127.0.0.1:8000`

## 零、2026-03-18 最终实施基线（给其他模型的强约束版本）

本节是**实现优先级最高**的执行说明。若与本文其他段落存在细微冲突，以本节为准。

### 0.1 目标边界（必须同时满足）

1. 用户在 AI 处理中继续发送的消息不能丢失。
2. 用户出现“算了/不用了/先这样”等取消表达后，旧轮次回复不能再下发。
3. 回调接口必须快速 ack，不同步等待 AI。
4. 多实例、服务重启后，队列状态可恢复。
5. 保留 `/api/doubao/chat` 作为调试与回退链路，不改其语义。

### 0.2 本次实现范围（P0 必做）

必须新增并接入以下模块：

- `src/services/queue/message_models.py`
- `src/services/queue/intent_classifier.py`
- `src/services/queue/queue_store.py`
- `src/services/queue/message_orchestrator.py`
- `src/services/queue/reply_delivery_service.py`
- `src/workers/message_queue_worker.py`
- `src/workers/reply_sender_worker.py`
- `src/api/routes/xiaohongshu_ingest.py`

必须新增入口：

- `POST /api/xiaohongshu/messages/ingest`

### 0.3 Redis Key 与字段（不可擅改）

| Key | 类型 | 说明 |
|------|------|------|
| `mq:session:{account_id}` | String/JSON | 会话状态 |
| `mq:seq:{account_id}` | String | 单用户自增序号 |
| `mq:msg:{account_id}:{seq}` | String/JSON | 入站消息 |
| `mq:ready_users` | ZSET | 待执行用户 |
| `mq:outbox:{job_id}` | String/JSON | 待投递任务 |
| `mq:outbox:ready` | ZSET | 待投递 job 索引 |
| `mq:dedupe:{platform_msg_id}` | String | 平台去重键 |
| `lock:mq:user:{account_id}` | String | 用户级分布式锁 |

`mq:session:{account_id}` 字段最小集合：

```json
{
  "state": "IDLE",
  "generation": 0,
  "version": 1,
  "debounce_until_ms": 0,
  "first_enqueue_at_ms": 0,
  "last_consumed_seq": 0,
  "max_enqueued_seq": 0,
  "active_turn_id": "",
  "dirty": false,
  "fail_streak": 0,
  "updated_at_ms": 0
}
```

### 0.4 状态机（不可偏离）

只允许三个落库状态：

- `IDLE`
- `DEBOUNCING`
- `RUNNING`

入站迁移：

- `IDLE` + 普通消息 -> `DEBOUNCING`
- `DEBOUNCING` + 普通消息 -> `DEBOUNCING`（刷新 debounce）
- `RUNNING` + 普通消息 -> `RUNNING`（仅 `dirty=true`）

worker 迁移：

- `DEBOUNCING` 到点 -> `RUNNING`
- `RUNNING` 完成且无新消息 -> `IDLE`
- `RUNNING` 完成且有新消息 -> `DEBOUNCING`（`now + MQ_RUNNING_RECHECK_MS`）

### 0.5 关键参数默认值（首版强制）

```python
MQ_ENABLED = True
MQ_DEBOUNCE_MS = 1000
MQ_DEBOUNCE_APPEND_MS = 800
MQ_DEBOUNCE_MAX_MS = 2000
MQ_RUNNING_RECHECK_MS = 300
MQ_SESSION_TTL_SECONDS = 604800
MQ_DEDUPE_TTL_SECONDS = 86400
MQ_MAX_PENDING_MESSAGES = 20
MQ_MAX_COMBINED_CHARS = 4000
MQ_READY_BATCH_SIZE = 100
MQ_OUTBOX_BATCH_SIZE = 100
MQ_OUTBOX_MAX_RETRIES = 8
MQ_RUNNING_STALE_AFTER_MS = 120000
MQ_RECOVERY_BATCH_SIZE = 200
MQ_WORKER_POLL_MS = 100
MQ_SENDER_POLL_MS = 500
MQ_LOCK_TTL_SECONDS = 180
```

### 0.6 12 项关键优化（纳入正式实现）

#### P0（上线前必须完成）

1. 入队背压：`pending > MQ_MAX_PENDING_MESSAGES` 返回 `queue_full`，拒绝入队并告警。
2. 发送幂等：sender 调平台发送时必须携带幂等键（建议 `client_msg_id=job_id`）。
3. 恢复扫描节流：每轮最多恢复 `MQ_RECOVERY_BATCH_SIZE` 个 RUNNING 会话。
4. 单用户失败熔断：`fail_streak` 超阈值后延迟重试，避免热故障循环。
5. 合并截断保留末条：消息超长时优先保留最后一条用户补充。
6. 时间戳容错：`timestamp` 解析失败不拒绝处理，仅记录指标。

#### P1（首版建议同步完成）

7. session `version` 字段：用于后续结构迁移。
8. 闭环成功率指标：`ingest -> delivery` 成功率必须可观测。
9. 空回复分类指标：区分业务静默与异常空串。
10. 取消词误判保护：避免“不是算了”这类否定句误触发 cancel。
11. ready 调度 jitter：重调度加小抖动，降低同秒尖峰。
12. 运维 runbook：Redis 故障、发送持续失败、队列积压三类应急手册。

#### P2（后置进阶优化，不阻塞首版上线）

- 多优先级队列（cancel/high-value 优先）
- 自适应 debounce
- 热点用户隔离 worker 池
- 历史压缩降 token
- 发送通道双活
- 运营可视化面板

### 0.7 原子入队（必须保证）

`enqueue_message()` 必须保证以下动作单次事务化完成（推荐 Lua）：

1. dedupe 检查
2. dedupe 写入
3. seq 自增
4. msg 写入
5. session 更新
6. ready_users 调度
7. 返回 `{accepted, state, seq}`

若不能保证原子性，本方案视为未完成。

### 0.8 worker 执行顺序（必须一致）

`run_user_turn(account_id)` 固定顺序：

1. 获取用户锁
2. 校验 session 可执行性
3. `start_turn`
4. 拉取 `start_seq~end_seq` 消息
5. 按序合并（保留换行，不改写）
6. 构造 `ChatRequest`
7. 调用 `ChatService.process_chat_request()`
8. 二次读 session 判 stale
9. stale -> `mark_turn_stale`
10. 非 stale -> `write_outbox`
11. `finish_turn_success` / `mark_turn_failed`
12. 释放用户锁

### 0.9 上线验收标准（全部通过才可上线）

1. AI 处理中连续发 5 条消息，最终均被消费（不丢不乱序）。
2. AI 处理中发送取消语义，旧 turn 回复不下发。
3. 重复 `platformMsgId` 回调只处理一次。
4. worker 重启后未消费消息可继续执行。
5. outbox 发送失败可重试并最终成功或进入告警。
6. 队列积压触发背压，不出现无界增长。

### 0.10 无灰度上线要求（当前项目适配）

由于当前无灰度系统，必须满足：

1. 保留 `/api/doubao/chat` 回退路径。
2. 新回调入口仅走 `/api/xiaohongshu/messages/ingest`。
3. 通过 `MQ_ENABLED` 提供一键熔断能力。
4. 上线当日重点监控：`pending_depth`、`sender_success_rate`、`stale_drop_count`。

## 一、目标

为小红书接入场景实现一套可生产落地的消息编排能力，解决以下问题：

1. 用户可以连续发送多条短消息，不被 `isProcessing=true` 阻塞。
2. AI 长时间处理中，后续消息不会丢失。
3. 用户补充信息时，后续轮次能看到新消息。
4. 用户改变主意时，旧回复不会再错误下发。
5. 多实例部署下，状态一致、可恢复、可观测。

## 一点一、2026-03-18 时延优化最终方案（不改业务逻辑版）

> 适用前提：不修改 `06_CONTACT_COLLECTION.md` 规则，不改变现有对话状态机语义，不降低拟人化要求。
> 执行优先级：高。若与历史参数建议冲突，以本节为准。

### 1. 目标指标

1. `P50 < 6s`
2. `P95 < 12s`
3. `P99 < 20s`
4. 108 场景通过率不低于当前基线
5. `contact_* / faq_priority_* / humanlike_*` 不退化

### 2. 分层实施策略

1. P0（工程层）：只改队列/轮询/超时/重试，不改对话规则
2. P1（行为等价）：提示词瘦身与 FAQ 短路，不改规则语义
3. P2（智能路由）：上下文长度 + 意图复杂度 + 风险等级路由，并带质量守门

### 3. P0 必做项（立即执行）

| 环节 | 动作 | 预计降时（常见） | 预计降时（长尾） |
|---|---|---:|---:|
| 队列防抖 | `debounce=300ms, append=200ms, max=1200ms` | 1.5~3.5s | 2~5s |
| MQ worker 轮询 | `poll_ms: 100 -> 20` | 0.2~0.8s | 0.5~1.5s |
| sender 轮询 | `poll_ms: 500 -> 100` | 0.1~0.5s | 0.3~1.0s |
| 前端回执轮询 | `1000ms -> 250ms` | 0.3~0.8s | 0.3~1.0s |
| AI 快失败 | 在线链路 `retry: 3 -> 1`，`timeout: 120 -> 45` | 0~1s | 5~20s |
| Redis 异常熔断 | 不可用时短期熔断，避免每请求重连抖动 | 0.2~1.0s | 1~3s |

> P0 合计预估：
> 常见轮次降低 `3~8s`，长尾轮次降低 `8~25s`。

### 4. P1 建议项（P0稳定后执行）

| 环节 | 动作 | 预计降时（常见） | 预计降时（长尾） |
|---|---|---:|---:|
| 提示词等价瘦身 | 去重、按场景拼接、短句化（不改规则） | 2~5s | 4~10s |
| FAQ短路 | 标准FAQ模板直出，绕过重推理 | 3~8s（FAQ轮） | 3~8s（FAQ轮） |
| completion 控长 | 减少冗余句，不改语气风格 | 0.5~2s | 1~4s |

> P1 叠加后预估：
> 常见轮次再降 `3~7s`，长尾再降 `5~12s`。

### 5. P2 进阶项（可后置）

1. 智能路由：仅低风险轮次走快模型，高风险轮次强制重模型。
2. 风险等级必须包含：联系方式拒绝、收尾判定、隐私顾虑、多意图冲突。
3. 质量守门：低质量自动升级重模型重答，不直接下发。

预估：常见 `1.5~4s`，长尾 `2~8s`。

### 6. 质量与拟人化守门（强约束）

1. 规则冻结：不得更改 `06_CONTACT_COLLECTION.md` 语义与流程边界。
2. 回归门槛：108 场景通过率不得下降。
3. 子集门槛：`contact_* / faq_priority_* / humanlike_*` 全量不退化。
4. 人工抽检：至少 30 段对话，拟人化评分不低于基线。

### 7. 执行清单（跨模型协作）

1. 先做 P0 并提交参数变更
2. 跑 108 场景并记录前后时延对比
3. 若门槛通过，再做 P1
4. 更新：
   - `docs/message_queue_status.yaml`
   - `reports/mq/p*_acceptance_*.md`
5. 任一关键门槛不达标，立即回滚到上一步

### 8. 当前执行状态（本轮）

1. 文档：`DONE`
2. P0 参数层：`IN_PROGRESS`
3. P1 提示词层：`PENDING`
4. P2 路由层：`PENDING`

## 零点一、2026-03-18 优化后最终执行版（主执行章节）

> 本章节是当前“最终执行版”。其他历史章节保留作背景说明；若出现冲突，以本章节为准。

### 0.1 执行边界（不允许偏离）

1. 不修改 `06_CONTACT_COLLECTION.md` 的业务规则定义、字段语义和收集约束。
2. 仅在消息编排层、调度层、发送层和表达层做优化。
3. 小红书正式链路必须走异步队列，不再以 `/api/doubao/chat` 作为主入口。

### 0.2 最终目标（上线判定）

1. AI 处理中用户连续发消息，零丢失、零乱序、零重复处理。
2. 连发场景下优先“单轮整合回复”，避免机械一问一答。
3. 端到端链路可观测、可告警、可恢复、可回滚。

### 0.3 主链路（必须采用）

1. 入站：`POST /api/xiaohongshu/messages/ingest`（快速 `accepted`，不阻塞 AI）。
2. 存储：Redis 作为状态真相源，入队原子化（Lua）。
3. 处理：`message_queue_worker` 按 `session_id` 串行执行。
4. 投递：`reply_sender_worker` 从 outbox 发送，失败重试，超限入死信。
5. 调试：`/api/doubao/chat` 仅保留为应急回退和本地调试入口。

### 0.4 连发拟人化策略（在不改业务规则前提下）

1. 短窗聚合：默认 `mq_debounce_ms=1500`，`mq_debounce_max_ms=4000`。
2. 语义触发：若意图已完整，可提前触发生成，不强等满窗口。
3. 单轮回复结构：先确认已收集信息，再问一个主问题。
4. 提问冷却：同字段 2 轮内禁止重复追问，除非用户主动回填该字段。
5. 跳过稳定：字段进入 `skip` 后在冷却窗口内不得再次主动追问。
6. 小红书连发增强：推荐将 `mq_debounce_max_ms` 提升到 `5000~6000ms`，优先把同一波短时连发合并到一个 turn。
7. 过早跳过防抖：未出现明确拒答语义时，不得因短时连续追问直接标记字段 `skip`。

### 0.5 配置基线（生产建议）

```ini
MQ_ENABLED=true
MQ_DEBOUNCE_MS=1500
MQ_DEBOUNCE_MAX_MS=5000
MQ_BATCH_MAX_MESSAGES=8
MQ_LOCK_TTL_MS=45000
MQ_OUTBOX_MAX_RETRIES=8
MQ_FAIL_STREAK_THRESHOLD=3
MQ_PRIORITY_BOOST_MS=1200
MQ_HOT_SESSION_THRESHOLD=20
MQ_FIELD_ASK_COOLDOWN_TURNS=2
MQ_SKIP_GUARD_ENABLED=true
```

### 0.5.1 TTL 分环境推荐清单（开发/测试/生产）

> 目的：避免把 `chat` 用户状态 TTL 和 `mq` 会话 TTL 配成同一值，导致重启恢复或上下文保留异常。

| 环境 | `REDIS_TTL`（chat 用户状态） | `MQ_SESSION_TTL_SECONDS`（mq 会话） | `MQ_DEDUPE_TTL_SECONDS`（mq 去重） | 说明 |
|------|------------------------------|-------------------------------------|------------------------------------|------|
| 开发（本地） | `3600`（1h） | `86400`（1d） | `21600`（6h） | 便于快速验证与清理，仍保留基本恢复能力 |
| 测试（联调/预发） | `21600`（6h） | `259200`（3d） | `43200`（12h） | 支持长链路回放与重启恢复测试 |
| 生产 | `86400`（24h） | `604800`（7d） | `86400`（24h） | 推荐基线；`mq` TTL 明显长于 chat TTL |

约束：

1. `MQ_SESSION_TTL_SECONDS` 必须 `>= REDIS_TTL`。
2. `MQ_DEDUPE_TTL_SECONDS` 不应低于平台重试窗口，建议至少 24h（生产）。
3. `REDIS_TTL=60`（1 分钟）仅适合临时调试，不适合稳定回归或线上环境。

可直接复制到 `.env`（生产）：

```ini
REDIS_TTL=86400
MQ_SESSION_TTL_SECONDS=604800
MQ_DEDUPE_TTL_SECONDS=86400
```

### 0.6 接入方契约（3chat.ai / 小红书调用方）

1. 入站必须提供：`session_id`、`platform_msg_id`、`timestamp`、`content`。
2. `platform_msg_id` 必须唯一（至少会话内唯一），用于幂等去重。
3. 调用方收到 `accepted` 即返回，不等待 AI 最终回复。

### 0.7 测试页面要求（避免“测到假链路”）

1. `test_page/static/mobile_final.html` 主调用改为 `ingest`（不得再直调 `/api/doubao/chat` 作为主测）。
2. 页面通过轮询或 SSE 获取 AI 回执并展示。
3. 必测脚本：1 秒内连发 4 条，期望单轮整合回复且不重复追问同字段。

### 0.8 观测与告警（必须落地）

1. 核心指标：`ingest_qps`、`dedupe_hit`、`pending_depth`、`turn_latency`、`sender_success_rate`、`stale_drop_count`、`dead_letter_count`。
2. 面板入口：`/api/doubao/mq/dashboard`。
3. 告警阈值建议：
   - `pending_depth > 200` 持续 5 分钟；
   - `sender_success_rate < 95%`；
   - `turn_latency_p95 > 8s` 持续 10 分钟。

### 0.9 强验收（无灰度场景）

1. 连发可靠性：1000 组连发用例，消息丢失率 = 0。
2. 幂等正确性：重复 `platform_msg_id` 只处理一次。
3. 顺序正确性：同 `session_id` 回复顺序稳定。
4. stale 生效：取消/结束后旧 generation 回复不下发。
5. 恢复能力：worker 重启后 pending 消息可继续消费。
6. 性能目标：端到端 `P95 < 8s`，`P99 < 15s`。
7. 对话质量：同字段（如年龄）不得连续两轮主动追问。
8. 跳过准确性：用户未明确拒答时，不得出现 `年龄: 跳过` 等过早 skip。
9. 连发整合：1 秒内连发 4 条，期望 1 条整合回复（允许最多 2 条）。

### 0.10 发布与回滚（一次到位）

1. 发布顺序：
   - 切小红书入口到 `ingest`；
   - 测试页切到 `ingest + 回执`；
   - 执行连发专项回归；
   - 再执行全量回归。
2. 回滚策略：
   - 通过 `MQ_ENABLED` 一键熔断新链路；
   - `/api/doubao/chat` 作为应急兜底路径保留。

## 二、结论

原设计稿中“短暂缓冲 + 队列串行处理”的产品思路是对的，但“内存 session + asyncio task”的实现方式只适合单机 PoC，不适合生产。

本方案采用以下原则：

- 保留短消息缓冲策略。
- 使用 Redis 作为会话状态的唯一真相源。
- 每个用户同一时刻只允许一个 worker 处理。
- 不强行取消正在运行的 LLM 调用，而是使用“过期回复丢弃”机制处理打断。
- 入站接收、AI 处理、回复投递三段解耦。

## 三、为什么不采用旧方案

旧方案的问题主要在工程实现层面：

1. `sessions: dict` 和 `asyncio.Task` 仅在单进程内有效，服务重启或多实例扩容会丢状态。
2. 后台任务拿到 AI 回复后，没有可靠投递链路，接口返回和消息下发语义不完整。
3. 没有消息幂等和去重设计，平台重试会导致重复处理。
4. 没有“过期回复判定”，用户说“算了”后旧结果仍可能发送。
5. 状态更新不是原子的，并发情况下容易互相覆盖。
6. 无法做稳定的监控、补偿、超时恢复和灰度上线。

## 四、设计原则

### 4.1 用户体验原则

- 用户发消息后必须立即得到平台侧 `ack`。
- 0.8 到 1.2 秒内的连续短消息应自动合并。
- AI 处理期间允许继续发消息。
- 用户明确结束或反悔后，旧结果必须失效。

### 4.2 工程原则

- 单用户串行，多用户并行。
- 状态持久化优先，不依赖进程内内存。
- 所有关键写操作要求幂等。
- 允许最终一致，不要求强同步返回 AI 文本。

## 五、总体架构

```text
小红书回调
   |
   v
Message Ingress API
   |
   | 1. 幂等校验
   | 2. 消息入 inbox
   | 3. 更新 session / debounce_until
   v
Redis
   |- mq:session:{user_id}
   |- mq:inbox:{user_id}
   |- mq:ready_users
   |- mq:outbox
   |- mq:dedupe:{platform_msg_id}
   |
   v
Queue Worker
   |
   | 1. 获取用户级锁
   | 2. 合并本轮消息
   | 3. 调用 ChatService
   | 4. 写出 outbox 或丢弃过期结果
   v
Reply Sender
   |
   v
小红书发送接口
```

## 六、职责边界

### 6.1 保留现有服务职责

`ChatService.process_chat_request()` 继续作为“单轮对话引擎”使用，仅负责：

- 加载用户资料
- 构建 prompt
- 调用 AI
- 解析和落档
- 生成本轮回复

它不负责：

- 消息排队
- 定时缓冲
- 分布式并发控制
- 下游平台消息投递

### 6.2 新增编排层职责

新增 `MessageOrchestrator`，统一负责：

- 入站消息去重
- 缓冲合并
- 单用户串行调度
- generation 管理
- 过期回复丢弃
- 调用 `ChatService`
- 将回复写入 outbox

## 七、核心状态模型

### 7.1 会话状态

每个用户维护一个 session：

| 状态 | 含义 | 说明 |
|------|------|------|
| `IDLE` | 空闲 | 无待处理消息，也无运行中任务 |
| `DEBOUNCING` | 缓冲中 | 正等待用户把一段话说完 |
| `RUNNING` | AI 处理中 | 当前已有一个 worker 在处理 |
| `WAITING_NEXT_TURN` | 待下一轮 | 逻辑概念态，首版可不单独落库 |

说明：

- 不再使用 `QUEUED` 作为独立复杂状态。
- “排队”用 `last_consumed_seq < max_enqueued_seq` 表达，更稳定。
- 首版实现建议只落 3 个状态：`IDLE`、`DEBOUNCING`、`RUNNING`。
- `WAITING_NEXT_TURN` 在首版中用 `RUNNING + dirty=true` 表示，不需要单独持久化。

### 7.2 generation 机制

为每个用户维护 `generation`：

- 每次开始一个新处理轮次，记录当前 generation。
- 如果用户明确表达取消、结束、反悔，可将 session 的 `generation` 递增。
- AI 返回时，如果发现“本轮开始时的 generation”已落后于 session 当前值，则该回复视为过期，不投递。

这就是“语义取消”。

优点：

- 不依赖底层模型必须支持 cancel。
- 可以稳定解决“算了”“不用了”“下次再说”等打断场景。

## 八、Redis 数据模型

### 8.1 session

Key: `mq:session:{user_id}`

建议字段：

```json
{
  "state": "IDLE",
  "generation": 12,
  "debounce_until_ms": 0,
  "last_consumed_seq": 15,
  "max_enqueued_seq": 15,
  "active_turn_id": "",
  "dirty": false,
  "updated_at_ms": 0
}
```

字段说明：

- `state`: 当前状态
- `generation`: 当前有效代数
- `debounce_until_ms`: 本轮缓冲结束时间
- `last_consumed_seq`: 已被消费完成的最后一条消息序号
- `max_enqueued_seq`: 当前已入站的最大序号
- `active_turn_id`: 正在执行的轮次 ID
- `dirty`: 运行期间是否有新消息到达

### 8.2 inbox

Key: `mq:inbox:{user_id}`

存储每条原始入站消息，建议结构：

```json
{
  "seq": 16,
  "platform_msg_id": "xxx",
  "dialog_id": "xxx",
  "content": "她是哪里人呀",
  "arrived_at_ms": 1710000000000,
  "intent": {
    "cancel_like": false,
    "force_flush": false
  }
}
```

建议用 Redis List / Stream / Sorted Set 之一实现。当前项目为了简单可控，优先建议：

- 用 `seq` 作为单调递增编号
- 消息内容存 `Redis Hash` 或 `Redis JSON`
- 再通过 `session.last_consumed_seq` 和 `session.max_enqueued_seq` 判定待消费范围

### 8.3 ready_users

Key: `mq:ready_users`

Redis ZSET：

- member: `user_id`
- score: 下一次可执行时间戳毫秒值

作用：

- Worker 按时间扫描到期用户
- 避免为每个用户创建本地 timer task

### 8.4 outbox

Key: `mq:outbox`

用于存放待投递回复。每条记录至少包含：

- `user_id`
- `turn_id`
- `generation`
- `reply_text`
- `retry_count`
- `next_retry_at_ms`

### 8.5 dedupe

Key: `mq:dedupe:{platform_msg_id}`

用于平台回调去重。TTL 建议 24 小时。

## 九、处理流程

### 9.1 入站流程

用户消息到达 API 后：

1. 读取 `platform_msg_id`，若存在 dedupe 记录，直接返回成功。
2. 对消息做轻量规则识别：
   - 是否是取消意图
   - 是否是强制立即发送意图
   - 是否为空白或脏数据
3. 原子写入 inbox，递增 `max_enqueued_seq`。
4. 更新 session：
   - `IDLE` -> `DEBOUNCING`
   - `DEBOUNCING` -> 延长 `debounce_until_ms`
   - `RUNNING` -> `dirty=true`
5. 若命中取消意图：
   - `generation += 1`
   - 标记正在运行的结果未来一律视为过期
6. 将 `user_id` 写入 `mq:ready_users`
7. API 立即返回平台成功响应

### 9.2 debounce 策略

默认策略：

- 首条消息到达后，缓冲 1000ms
- 缓冲期间再来消息，重置到“当前时刻 + 800ms”
- 单轮最大缓冲窗口不超过 2000ms

原因：

- 2.5 秒在 IM 场景偏长
- 1 秒左右更像真人正在看消息
- 兼顾用户体验和合并效果

### 9.3 worker 执行流程

worker 从 `mq:ready_users` 取到到期用户后：

1. 获取 `lock:mq:user:{user_id}`，保证单用户串行。
2. 读取 session；如果 `debounce_until_ms` 还没到，则重新放回 ZSET。
3. 将 session 置为 `RUNNING`，生成 `turn_id`，记录 `turn_generation=session.generation`。
4. 读取本轮待消费消息：
   - 从 `last_consumed_seq + 1` 到 `max_enqueued_seq`
5. 将本轮消息合并成一个 `question`。
6. 调用现有 `ChatService.process_chat_request()`。
7. AI 返回后再次读取 session：
   - 如果 `session.generation != turn_generation`，则丢弃回复
   - 如果一致，写入 outbox
8. 更新 `last_consumed_seq`
9. 如果运行期间 `dirty=true` 且仍有新消息：
   - 改为 `DEBOUNCING`
   - 设置一个很短的 `debounce_until_ms`，建议 300ms
   - 重新放入 ready_users
10. 否则置为 `IDLE`

### 9.4 回复投递流程

独立 sender worker 负责：

1. 从 outbox 拉取待发送记录
2. 调用小红书发送接口
3. 成功后标记完成
4. 失败后指数退避重试
5. 达到上限后进入死信或告警

这样可以避免：

- AI 成功但发送失败时结果丢失
- API 线程直接承担外部发送的不稳定性

## 十、消息合并策略

### 10.1 合并规则

同一轮内将多条消息按顺序拼接：

```text
你好
我是看到帖子来的
想了解一下那个女生
她是哪里人呀
```

合并时保留换行，不做复杂语义改写。

### 10.2 不建议首版就做的事情

以下能力首版不要上：

- 相似语义去重
- 大模型总结后再发给主模型
- 多优先级复杂抢占
- 正在运行时真正中断 LLM socket

这些复杂度高，但首版收益不大。

## 十一、取消与结束语义

### 11.1 取消意图

建议识别以下文本特征：

- 算了
- 不用了
- 下次再说
- 不聊了
- 不想看了
- 先这样

命中后执行：

1. `generation += 1`
2. 本次消息照样入 inbox
3. 下一轮由 `ChatService` 输出自然收尾或静默
4. 当前运行中的旧回复回来后直接丢弃

### 11.2 为什么不用强制 cancel

原因：

- 底层模型调用不一定稳定支持取消
- 就算取消 HTTP 请求，也无法保证上游模型计算已停止
- 语义取消更容易保证正确性

## 十二、接口设计

### 12.1 小红书入站接口

建议新增异步入队接口：

`POST /api/xiaohongshu/messages/ingest`

请求字段建议：

```json
{
  "accountId": "u123",
  "dialogId": "d456",
  "message": "她是哪里人呀",
  "platformMsgId": "msg_789",
  "timestamp": "2026-03-17T10:00:00+08:00",
  "sex": "男"
}
```

响应建议：

```json
{
  "success": true,
  "accepted": true,
  "status": "queued"
}
```

说明：

- 不同步返回 AI 文本
- 只表示平台消息已接收

### 12.2 保留现有同步接口

现有测试页和调试链路可继续使用：

- `POST /api/doubao/chat`

用途：

- 本地调试
- 回归测试
- 不依赖消息队列的直连调用

不建议直接把它改造成生产回调主入口。

## 十三、与现有代码的集成方式

### 13.1 建议新增模块

建议新增：

- `src/services/queue/message_orchestrator.py`
- `src/services/queue/queue_store.py`
- `src/services/queue/reply_delivery_service.py`
- `src/workers/message_queue_worker.py`
- `src/workers/reply_sender_worker.py`

### 13.2 `ChatService` 集成方式

`MessageOrchestrator` 在执行轮次时，将合并后的文本封装成 `ChatRequest`：

```python
ChatRequest(
    question=combined_message,
    accountId=user_id,
    dialogId=dialog_id,
    sex=sex,
    timestamp=timestamp,
)
```

然后调用：

```python
await chat_service.process_chat_request(chat_request)
```

### 13.3 现有同步上下文仍可复用

现有以下能力无需重写：

- 用户画像读写
- 对话历史
- prompt 构建
- 联系方式校验
- 结束意图业务规则

新方案只是在其外面增加稳定的消息编排层。

## 十四、推荐代码结构

建议按以下文件拆分实现：

### 14.1 `src/services/queue/message_models.py`

定义数据结构：

- `IncomingMessage`
- `QueueSession`
- `TurnContext`
- `OutboxJob`
- `EnqueueResult`

建议字段如下：

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomingMessage:
    account_id: str
    dialog_id: Optional[str]
    content: str
    platform_msg_id: str
    timestamp: str
    sex: Optional[str] = None
    cancel_like: bool = False
    force_flush: bool = False


@dataclass
class QueueSession:
    account_id: str
    state: str
    generation: int
    debounce_until_ms: int
    last_consumed_seq: int
    max_enqueued_seq: int
    active_turn_id: str
    dirty: bool
    updated_at_ms: int


@dataclass
class TurnContext:
    turn_id: str
    account_id: str
    dialog_id: Optional[str]
    generation: int
    start_seq: int
    end_seq: int
    combined_message: str
    sex: Optional[str]
    timestamp: Optional[str]


@dataclass
class OutboxJob:
    job_id: str
    account_id: str
    turn_id: str
    generation: int
    reply_text: str
    dialog_id: Optional[str]
    retry_count: int
    next_retry_at_ms: int


@dataclass
class EnqueueResult:
    accepted: bool
    duplicate: bool
    session_state: str
    seq: int
```

### 14.2 `src/services/queue/intent_classifier.py`

只做轻量规则识别，不调用大模型。

必须提供：

```python
class QueueIntentClassifier:
    def classify(self, content: str) -> dict:
        return {
            "cancel_like": False,
            "force_flush": False,
        }
```

首版规则：

- `cancel_like`: 算了、不用了、不聊了、先这样、下次再说
- `force_flush`: 说完了、你回复吧、好了、可以回我了

### 14.3 `src/services/queue/queue_store.py`

负责所有 Redis 读写和原子操作。

必须提供以下接口：

```python
class QueueStore:
    async def enqueue_message(self, msg: IncomingMessage, now_ms: int) -> EnqueueResult: ...
    async def get_session(self, account_id: str) -> QueueSession: ...
    async def schedule_user(self, account_id: str, run_at_ms: int) -> None: ...
    async def fetch_ready_users(self, now_ms: int, limit: int = 100) -> list[str]: ...
    async def start_turn(self, account_id: str, now_ms: int) -> TurnContext | None: ...
    async def get_turn_messages(self, account_id: str, start_seq: int, end_seq: int) -> list[dict]: ...
    async def mark_turn_stale(self, account_id: str, turn: TurnContext, now_ms: int) -> None: ...
    async def finish_turn_success(self, account_id: str, turn: TurnContext, now_ms: int, has_more: bool) -> None: ...
    async def write_outbox(self, job: OutboxJob) -> None: ...
    async def fetch_due_outbox_jobs(self, now_ms: int, limit: int = 100) -> list[OutboxJob]: ...
    async def mark_outbox_done(self, job_id: str) -> None: ...
    async def retry_outbox(self, job_id: str, retry_count: int, next_retry_at_ms: int, error: str) -> None: ...
    async def recover_stale_running_sessions(self, now_ms: int, stale_after_ms: int) -> int: ...
```

### 14.4 `src/services/queue/message_orchestrator.py`

负责业务编排，不直接写 Redis 底层结构。

必须提供以下接口：

```python
class MessageOrchestrator:
    async def ingest(self, payload: dict) -> dict: ...
    async def run_user_turn(self, account_id: str) -> None: ...
```

### 14.5 `src/services/queue/reply_delivery_service.py`

负责调用小红书发送接口。

必须提供：

```python
class ReplyDeliveryService:
    async def send_reply(
        self,
        account_id: str,
        reply_text: str,
        dialog_id: str | None = None,
    ) -> None: ...
```

### 14.6 worker

新增两个 worker：

- `src/workers/message_queue_worker.py`
- `src/workers/reply_sender_worker.py`

二者都应实现：

- 常驻循环
- 单次批量拉取
- sleep 间隔
- 优雅停机
- 错误日志和自恢复

## 十五、配置项

建议新增以下配置到 `settings`：

```python
MQ_ENABLED: bool = True
MQ_DEBOUNCE_MS: int = 1000
MQ_DEBOUNCE_APPEND_MS: int = 800
MQ_DEBOUNCE_MAX_MS: int = 2000
MQ_RUNNING_RECHECK_MS: int = 300
MQ_SESSION_TTL_SECONDS: int = 604800
MQ_DEDUPE_TTL_SECONDS: int = 86400
MQ_MAX_PENDING_MESSAGES: int = 20
MQ_MAX_COMBINED_CHARS: int = 4000
MQ_READY_BATCH_SIZE: int = 100
MQ_OUTBOX_BATCH_SIZE: int = 100
MQ_OUTBOX_MAX_RETRIES: int = 8
MQ_RUNNING_STALE_AFTER_MS: int = 180000
MQ_WORKER_POLL_MS: int = 200
MQ_SENDER_POLL_MS: int = 500
MQ_LOCK_TTL_SECONDS: int = 180
MQ_LOCK_TIMEOUT_SECONDS: float = 1.0
```

默认值说明：

- `MQ_DEBOUNCE_MS=1000`: 首条消息缓冲 1 秒
- `MQ_DEBOUNCE_APPEND_MS=800`: 新消息到来时向后推 0.8 秒
- `MQ_DEBOUNCE_MAX_MS=2000`: 单轮最长不超过 2 秒
- `MQ_RUNNING_RECHECK_MS=300`: 运行期间有新消息时，下一轮只短等 300ms

## 十六、Redis Key 约定

必须统一 key 命名，避免不同实现模型各写一套。

| Key | 类型 | 说明 |
|------|------|------|
| `mq:session:{account_id}` | String/JSON | 用户 session |
| `mq:seq:{account_id}` | String | 用户消息自增序号 |
| `mq:msg:{account_id}:{seq}` | String/JSON | 单条消息 |
| `mq:ready_users` | ZSET | 待调度用户 |
| `mq:outbox:ready` | ZSET | 待发送回复 job_id |
| `mq:outbox:{job_id}` | String/JSON | 回复任务 |
| `mq:dedupe:{platform_msg_id}` | String | 平台去重键 |
| `mq:turn:{account_id}:{turn_id}` | String/JSON | 可选，调试/恢复用 |

说明：

- 如果项目里没有 RedisJSON，统一用 `json.dumps` 存字符串。
- 所有 key 都要走项目已有 prefix。

## 十七、状态迁移规则

其他模型实现时，必须严格遵守下面的状态迁移。

### 17.1 入站消息导致的迁移

| 当前状态 | 条件 | 新状态 | 说明 |
|----------|------|--------|------|
| `IDLE` | 普通消息 | `DEBOUNCING` | 创建新一轮缓冲 |
| `DEBOUNCING` | 普通消息 | `DEBOUNCING` | 延长缓冲时间 |
| `RUNNING` | 普通消息 | `RUNNING` | 只设 `dirty=true` |

### 17.2 取消意图导致的迁移

| 当前状态 | 条件 | 新状态 | 额外动作 |
|----------|------|--------|----------|
| `IDLE` | cancel | `DEBOUNCING` | `generation += 1` |
| `DEBOUNCING` | cancel | `DEBOUNCING` | `generation += 1` |
| `RUNNING` | cancel | `RUNNING` | `generation += 1`, `dirty=true` |

### 17.3 worker 执行导致的迁移

| 当前状态 | 条件 | 新状态 | 说明 |
|----------|------|--------|------|
| `DEBOUNCING` | 到达执行时间 | `RUNNING` | start turn |
| `RUNNING` | 本轮结束且无新消息 | `IDLE` | finish turn |
| `RUNNING` | 本轮结束且有新消息 | `DEBOUNCING` | 下一轮短缓冲 |
| `RUNNING` | 结果过期 | `DEBOUNCING/IDLE` | 取决于是否还有未消费消息 |

## 十八、消息入队原子逻辑

`enqueue_message()` 必须是原子操作，推荐用 Lua 实现。

### 18.1 需要一次完成的动作

1. 检查 `mq:dedupe:{platform_msg_id}` 是否已存在
2. 若已存在，直接返回 duplicate
3. 写入 dedupe key
4. 递增 `mq:seq:{account_id}`
5. 写入 `mq:msg:{account_id}:{seq}`
6. 读取并更新 session
7. 写入 `mq:ready_users`
8. 返回新 seq 和状态

### 18.2 伪代码

```lua
if exists(dedupe_key) then
  return {0, "duplicate", 0}
end

setex(dedupe_key, dedupe_ttl, "1")
seq = incr(seq_key)
setex(msg_key(seq), session_ttl, message_json)

session = load_or_default(session_key)

if cancel_like then
  session.generation = session.generation + 1
end

session.max_enqueued_seq = seq
session.updated_at_ms = now_ms

if session.state == "IDLE" then
  session.state = "DEBOUNCING"
  session.debounce_until_ms = now_ms + debounce_ms
elseif session.state == "DEBOUNCING" then
  session.debounce_until_ms = min(
    max(session.debounce_until_ms, now_ms + debounce_append_ms),
    first_message_at_ms + debounce_max_ms
  )
elseif session.state == "RUNNING" then
  session.dirty = true
end

save(session_key, session)
zadd(ready_users_key, session.debounce_until_ms_or_now, account_id)
return {1, session.state, seq}
```

实现注意：

- “首条消息时间”如果不想单独存，首版可退化为 `min(now + append_ms, old_debounce_until + append_ms)`，但文档推荐显式记录。
- session 和 msg 都要带 TTL，防止垃圾堆积。

## 十九、worker 执行规格

### 19.1 `message_queue_worker.py`

主循环要求：

```python
while not stopped:
    now_ms = current_ms()
    user_ids = await queue_store.fetch_ready_users(now_ms, limit=settings.MQ_READY_BATCH_SIZE)
    if not user_ids:
        await asyncio.sleep(settings.MQ_WORKER_POLL_MS / 1000)
        continue

    for account_id in user_ids:
        try:
            await orchestrator.run_user_turn(account_id)
        except Exception:
            logger.exception("run_user_turn failed", extra={"account_id": account_id})
```

### 19.2 `run_user_turn(account_id)` 详细步骤

必须按以下顺序：

1. 获取用户锁
2. 读取 session，不满足执行条件则 reschedule 并退出
3. `start_turn()`
4. 读取 `start_seq ~ end_seq` 全部消息
5. 按顺序拼接消息
6. 截断到最大长度
7. 构造 `ChatRequest`
8. 调用 `chat_service.process_chat_request`
9. 取 `result["response"]`
10. 二次读取 session 判定是否 stale
11. stale 则 `mark_turn_stale`
12. 非 stale 则写 outbox
13. `finish_turn_success`

### 19.3 合并消息实现规则

```python
def combine_messages(messages: list[dict], max_chars: int) -> str:
    parts = []
    total = 0
    for item in messages:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if parts:
            candidate = total + 1 + len(content)
        else:
            candidate = total + len(content)
        if candidate > max_chars:
            break
        parts.append(content)
        total = candidate
    return "\n".join(parts)
```

实现注意：

- 不能打乱消息顺序
- 不能擅自改写原文
- 不要在队列层做 NLP 总结

## 二十、`start_turn()` 精确定义

`start_turn(account_id, now_ms)` 的职责：

1. 读取 session
2. 若 `state != DEBOUNCING`，返回 `None`
3. 若 `debounce_until_ms > now_ms`，返回 `None`
4. 令：
   - `start_seq = last_consumed_seq + 1`
   - `end_seq = max_enqueued_seq`
5. 若 `start_seq > end_seq`，则置 `IDLE` 并返回 `None`
6. 生成 `turn_id`
7. 将 session 更新为：
   - `state = RUNNING`
   - `active_turn_id = turn_id`
   - `dirty = false`
   - `updated_at_ms = now_ms`
8. 返回 `TurnContext`

注意：

- `generation` 在这里读取一次并写入 `TurnContext`
- `TurnContext` 是这轮的只读快照，后续不要在业务代码里修改

## 二十一、stale 判定与完成逻辑

### 21.1 stale 判定条件

满足任意一条就视为 stale：

1. `current_session.generation != turn.generation`
2. `current_session.active_turn_id != turn.turn_id`

第 2 条用于避免 worker 崩溃恢复后旧任务回写。

### 21.2 `mark_turn_stale()`

需要完成：

1. 更新 `last_consumed_seq = turn.end_seq`
2. 如果还有未消费消息：
   - `state = DEBOUNCING`
   - `debounce_until_ms = now_ms + MQ_RUNNING_RECHECK_MS`
3. 否则：
   - `state = IDLE`
4. 清空 `active_turn_id`
5. 记录 stale 指标

### 21.3 `finish_turn_success()`

需要完成：

1. 更新 `last_consumed_seq = turn.end_seq`
2. 若 `last_consumed_seq < max_enqueued_seq`：
   - `state = DEBOUNCING`
   - `debounce_until_ms = now_ms + MQ_RUNNING_RECHECK_MS`
3. 否则：
   - `state = IDLE`
4. 清空 `active_turn_id`
5. `dirty = false`

## 二十二、outbox 实现规格

### 22.1 为什么必须做 outbox

其他模型实现时不要省略 outbox。

原因：

- AI 成功不等于消息已发出去
- 下游平台接口可能超时、429、5xx
- 没有 outbox 就无法保证回复可靠送达

### 22.2 `write_outbox()`

创建 job 后必须：

1. 写入 `mq:outbox:{job_id}`
2. `zadd mq:outbox:ready next_retry_at_ms`

### 22.3 sender worker 重试规则

建议指数退避：

- 第 1 次失败：5 秒
- 第 2 次失败：15 秒
- 第 3 次失败：30 秒
- 第 4 次失败：60 秒
- 之后每次：300 秒封顶

伪代码：

```python
delay = min(300, [5, 15, 30, 60][retry_count - 1] if retry_count <= 4 else 300)
next_retry_at_ms = now_ms + delay * 1000
```

### 22.4 sender 成功条件

只有在小红书发送接口明确返回成功时，才能：

- `mark_outbox_done(job_id)`
- 上报发送成功指标

不能以“请求发出”视为成功。

## 二十三、异常与边界处理

### 23.1 平台重复回调

必须用 `platformMsgId` 去重。

如果平台没有稳定消息 ID，则退化为：

- `sha1(account_id + dialog_id + content + rounded_timestamp)`

但这只是兜底，不如平台原始 ID 稳。

### 23.2 空消息

空白消息直接拒绝入队：

```json
{
  "success": true,
  "accepted": false,
  "status": "ignored_empty"
}
```

### 23.3 超长消息

若单条消息超长：

- 原文入队
- 执行轮次时截断到 `MQ_MAX_COMBINED_CHARS`
- 记录 warn 日志

不要在入队阶段直接丢弃。

### 23.4 `ChatService` 返回空串

如果 `result["response"] == ""`：

- 仍视为一次成功轮次
- 不写 outbox
- 正常 `finish_turn_success`

因为当前业务里空响应是合法语义。

### 23.5 worker 中途异常

若 `process_chat_request()` 抛异常：

- 记录错误
- 将 session 恢复到 `DEBOUNCING`
- `debounce_until_ms = now_ms + MQ_RUNNING_RECHECK_MS`
- 不推进 `last_consumed_seq`

这样允许下一轮重试。

## 二十四、日志要求

其他模型实现时必须统一打关键日志，便于排查。

建议日志点：

- ingest 开始/结束
- dedupe 命中
- enqueue 成功
- start_turn
- combined_message 长度和消息条数
- stale drop
- outbox write
- sender success/failure
- recovery 扫描结果

日志字段最少包含：

- `account_id`
- `turn_id`
- `generation`
- `start_seq`
- `end_seq`

## 二十五、测试清单

### 25.1 单元测试文件建议

- `tests/unit/test_queue_intent_classifier.py`
- `tests/unit/test_queue_store.py`
- `tests/unit/test_message_orchestrator.py`
- `tests/unit/test_reply_delivery_service.py`

### 25.2 必测场景

1. 首条消息进入 `DEBOUNCING`
2. 第二条消息重置 debounce
3. worker 到点后能正确拼接 2 到 5 条消息
4. `RUNNING` 期间来新消息，`dirty=true`
5. `RUNNING` 期间收到 cancel，generation 递增
6. 旧 turn 返回后被 stale 丢弃
7. turn 成功后写入 outbox
8. outbox 发送失败会重试
9. dedupe 命中时不重复入队
10. worker 崩溃恢复后 session 能重新调度

### 25.3 验收标准

满足以下条件才算实现完成：

1. 连续发送 4 条短消息，最终只调用一次 `ChatService`
2. AI 处理中再次发消息，旧轮结束后会触发下一轮
3. AI 处理中发送“算了”，旧轮结果不再发送
4. 平台重复回调不会触发重复回复
5. sender 失败后最多重试到配置上限
6. Redis 中不会无限堆积过期 session 和消息

## 二十六、实施注意点

这是给其他模型实现时最容易踩坑的地方。

### 26.1 不要把队列逻辑塞进 `ChatService`

`ChatService` 是单轮引擎，不要把：

- Redis 队列
- debounce
- worker 调度
- outbox 发送

写进 `ChatService` 内部。

### 26.2 不要依赖进程内内存保存 session

以下数据不能只放内存：

- 当前 state
- generation
- pending seq
- outbox job

否则多实例会错。

### 26.3 不要试图真正取消 LLM 请求

首版只做 stale drop。

强制 cancel：

- 复杂
- 不稳定
- 容易引入半成功状态

### 26.4 不要在队列层做复杂语义处理

队列层只做编排，不做智能总结。

否则：

- 容易破坏原始上下文
- 增加额外模型调用
- 调试困难

### 26.5 不要遗漏 TTL

以下 key 必须有 TTL 或显式清理：

- session
- msg
- dedupe
- turn debug key

否则 Redis 会变成垃圾场。

### 26.6 不要把“空回复”当异常

当前项目已有合法空回复场景。

所以：

- 空回复不发 outbox
- 但 turn 要正常结束

## 二十七、原子性要求

以下操作建议使用 Lua 脚本或事务保证原子性：

1. 幂等检查 + inbox 入队 + session 更新
2. worker 抢占用户执行权
3. 完成轮次后更新 `last_consumed_seq` 和 `state`

否则容易出现：

- 重复消费
- 漏消费
- 状态回退
- 多 worker 同时处理同一用户

## 二十八、锁设计

每个用户使用一把分布式锁：

- Key: `lock:mq:user:{user_id}`
- TTL: 180 秒
- 开启自动续租

说明：

- TTL 要覆盖 120 秒 AI 超时 + 状态收尾时间
- 若现有锁组件复用，需要先修正重复 acquire 问题

## 二十九、失败恢复

### 29.1 worker 崩溃

worker 崩溃后：

- 锁过期自动释放
- 用户 session 仍在 Redis 中
- `mq:ready_users` 中仍可重新调度

恢复策略：

- 启动时扫描 `RUNNING` 且长时间未更新的 session
- 将其回滚到 `DEBOUNCING` 或 `IDLE`

### 29.2 AI 超时

AI 超时后：

- 本轮记失败
- 不清空未消费消息
- 由策略决定：
  - 返回空回复并继续下一轮
  - 或投递固定兜底文案

不建议直接“超时后清空所有队列”。

### 29.3 下游发送失败

发送失败时：

- outbox 保留
- 指数退避重试
- 达到上限后告警

## 三十、容量与限制

建议首版限制：

- 单用户待处理消息条数上限：20
- 单轮合并总长度上限：4000 字符
- outbox 重试上限：8 次
- dedupe TTL：24 小时
- session TTL：7 天

超过限制时：

- 优先保留最新消息
- 记录告警日志
- 指标上报

## 三十一、监控指标

必须接入以下指标：

- `mq_ingress_total`
- `mq_dedupe_hit_total`
- `mq_debounce_merge_total`
- `mq_turn_started_total`
- `mq_turn_timeout_total`
- `mq_stale_reply_drop_total`
- `mq_outbox_send_success_total`
- `mq_outbox_send_retry_total`
- `mq_outbox_send_failed_total`
- `mq_queue_depth_current`
- `mq_turn_latency_ms`
- `mq_delivery_latency_ms`

重点观察：

- 每用户积压深度
- 过期回复丢弃率
- AI 超时率
- 平均缓冲命中次数

## 三十二、测试方案

### 32.1 单元测试

覆盖：

- 连续 2 到 5 条消息合并
- `RUNNING` 期间新消息到达
- 取消意图导致 generation 递增
- 旧回复被判定为 stale
- dedupe 生效
- 队列上限保护

### 32.2 集成测试

覆盖：

- Redis 下多 worker 并发
- worker 崩溃恢复
- outbox 发送失败重试
- AI 超时场景

### 32.3 端到端测试

覆盖典型用户场景：

1. 连发 4 条短消息
2. AI 思考中继续补充
3. 中途说“算了”
4. 联系方式收集阶段连续确认词
5. 平台重复回调

## 三十三、分阶段上线建议

### 阶段 1：只做 debounce 合并

目标：

- 先解决连续短消息问题
- 保持单实例或单用户串行

范围：

- 入队
- 合并
- 调用 `ChatService`

### 阶段 2：补齐分布式串行和 outbox

目标：

- 支持多实例
- 回复投递可靠

范围：

- Redis session
- 分布式锁
- outbox sender

### 阶段 3：补齐 stale reply discard 和恢复能力

目标：

- 稳定支持“算了/不聊了”等打断
- 增强故障恢复

范围：

- generation
- 崩溃恢复扫描
- 监控告警

## 三十四、最终推荐

最终推荐的首版落地范围如下：

必须做：

- Redis 持久化 session
- 单用户串行 worker
- 1 秒左右 debounce
- 幂等去重
- outbox 投递
- generation 过期回复丢弃
- 基础监控

可以二期再做：

- 更复杂的意图分类
- 动态 debounce
- 相似消息归并
- 更细粒度优先级

## 三十五、实施清单

1. 新增 `queue_store`，封装 Redis key 和原子操作。
2. 新增 `MessageOrchestrator`，负责 ingest 和 turn 调度。
3. 新增 worker，消费 `mq:ready_users`。
4. 新增 outbox sender。
5. 增加小红书异步 ingest 路由。
6. 复用 `ChatService.process_chat_request()` 作为单轮引擎。
7. 补齐测试、指标、告警。
8. 灰度上线并观察积压、超时、stale drop。

---

## 三十六、附录：首版伪代码

### A. ingest

```python
async def ingest_message(msg):
    if await dedupe_exists(msg.platform_msg_id):
        return {"success": True, "accepted": True, "status": "duplicate"}

    result = await queue_store.enqueue(msg)
    return {"success": True, "accepted": True, "status": result.status}
```

### B. worker

```python
async def run_user_turn(user_id):
    async with user_lock(user_id):
        session = await queue_store.get_session(user_id)
        if not session.ready_to_run():
            await queue_store.reschedule(user_id, session.debounce_until_ms)
            return

        turn = await queue_store.start_turn(user_id)
        combined_message = await queue_store.load_turn_messages(user_id, turn)

        request = ChatRequest(
            question=combined_message,
            accountId=user_id,
            dialogId=turn.dialog_id,
            sex=turn.sex,
            timestamp=turn.timestamp,
        )

        result = await chat_service.process_chat_request(request)

        session_after = await queue_store.get_session(user_id)
        if session_after.generation != turn.generation:
            await queue_store.finish_turn_as_stale(user_id, turn)
            return

        await queue_store.write_outbox(user_id, turn, result["response"])
        await queue_store.finish_turn(user_id, turn)
```

### C. sender

```python
async def send_reply(job):
    try:
        await xhs_client.send_message(job.user_id, job.reply_text)
        await outbox.mark_done(job.id)
    except Exception:
        await outbox.retry_later(job.id)
```
