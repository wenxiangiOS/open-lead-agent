# 多次发送消息处理方案设计文档

> 创建时间：2026-03-06
> 最后更新：2026-04-13
> 状态：建议按本方案实施
> 文档类型：正式技术方案

## 执行入口（只记这一个文档）

后续无论是你本人还是其他模型协作，**只需要先打开本文件**，然后按下面 4 个入口执行：

1. 若目标是“小红书短时间连发最终尽量只回一条”，优先遵循 `零点二、2026-04-12 小红书 latest-wins 完整方案（专家修订版）`
2. 其余 MQ 通用边界与未冲突部分，再遵循 `零点一、2026-04-06 最终优化约束（职责边界收敛版）` 与 `零、2026-03-18 最终实施基线`
3. 当前进度：`docs/message_queue_status.yaml`
4. 验收证据：`reports/mq/p0_acceptance_*.md`

协作口令（可直接复制给其他模型）：

`先按 docs/07_MESSAGE_QUEUE_DESIGN.md 的“执行入口”和“零点二”章节实施；若零点二未覆盖，再遵循“零点一”和“零”；完成后更新 docs/message_queue_status.yaml，并提交 reports/mq/p0_acceptance_*.md。`

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

本节是**历史实施基线**。若与 `零点二`、`零点一` 冲突，以 `零点二` 优先、`零点一` 次之；其余未冲突部分仍可继续参考本节。

## 零点二、2026-04-12 小红书 latest-wins 完整方案（专家修订版）

> 本节是面向“小红书用户短时间连续补发多条消息，但用户侧最终尽量只收到 1 条 AI 回复”的正式方案。  
> 若与 `零点一`、`零`、`0.4 首版语义`、`0.4.1 后续真人化增强方案` 冲突，以本节为准。  
> 2026-04-13 更新：本仓库已完成本节核心改造并通过专项验收；状态以 `docs/message_queue_status.yaml` 的 `latest_wins_xhs` 与 `reports/mq/latest_wins_acceptance_20260413.md` 为准。

### 0.2.1 目标重定义

针对小红书这类“用户喜欢连发补充”的平台，最终目标不应是“每条入站消息都尽快回”，而应是：

1. 同一波连续输入，用户侧尽量只看到最后一条有效 AI 回复。
2. 用户在 AI 生成期间继续补发时，旧回复若已被新输入覆盖，则不再发送。
3. 不因只发最后一条回复而破坏资料收集、FAQ、联系方式、收尾等既有业务逻辑。
4. 不因体验优化引入业务状态重复提交、计数漂移、历史重复写入。

一句话原则：

- 系统内部允许多次生成
- 用户侧尽量只看到最后一条
- 旧回复不发送
- 旧状态不提交

### 0.2.2 核心判定原则（latest-wins）

本方案采用 `latest-wins`：

1. **最新输入优先于旧草稿**
   - 只要旧草稿覆盖范围之后又到达了新消息，旧草稿就失去发送资格。
2. **发送资格晚于生成完成**
   - “已经生成好”不等于“允许发送”。
3. **业务提交晚于发送确认**
   - 只有最终获胜的那一轮，才允许提交画像、历史、计数等业务副作用。
4. **cancel 仍然是强失效信号**
   - `cancel / 结束 / 反悔` 仍通过 `generation += 1` 直接让旧轮次失效。
5. **普通补发也是覆盖信号**
   - 即使不是 cancel，只要有更新消息到达，也会让旧草稿失去“最终发送资格”。

### 0.2.3 架构边界（必须按此拆分）

本方案必须把“生成”和“提交”拆开：

- MQ 负责：
  1. 接入、去重、排队
  2. burst debounce
  3. latest-wins 判定
  4. 候选 outbox 管理
  5. 发送前二次复核
  6. 崩溃恢复、重试、观测

- ChatService 负责：
  1. 业务语义判断
  2. FAQ / 联系方式 / 收尾等业务逻辑
  3. 生成回复文本
  4. 生成本轮业务状态变更草稿

- Sender / Finalizer 负责：
  1. 发送最终获胜回复
  2. 发送成功后提交本轮业务状态变更
  3. 推进已确认游标

强约束：

1. MQ 不能新增业务语义规则。
2. MQ 可以决定“这轮结果是否还有资格发送与提交”。
3. ChatService 可以继续做原有业务判断，但在 latest-wins 方案里不得直接写最终状态到真实存储。

### 0.2.4 为什么不能只做 sender 丢弃旧回复

只在 sender 层丢掉旧回复是不够的。

原因：

1. 当前 `ChatService` 不是纯函数，执行过程中会更新画像、历史、计数等状态。
2. 如果旧轮次已经把业务状态写入真实存储，即使最终不发送，业务状态也已经漂移。
3. 这样会出现：
   - 电话/微信追问计数被多加
   - 历史重复写入
   - 收尾状态提前推进
   - FAQ/主线恢复逻辑被旧轮污染

因此本方案必须采用：

- **先生成草稿**
- **后确认仍然最新**
- **最后发送并提交**

### 0.2.5 主键模型（必须收敛）

为避免同一账号下多个对话串线，本方案引入双主键：

1. `conversation_key = account_id + "::" + (dialog_id or "_")`
2. `profile_key = account_id`

用途：

- `conversation_key` 用于 MQ 排队、排序、latest-wins、outbox、恢复。
- `profile_key` 用于沿用当前用户画像、资料收集、联系方式等业务状态。

强约束：

1. MQ session 不得再仅以 `account_id` 作为唯一编排主键。
2. 同一 `account_id` 下不同 `dialog_id` 的消息不得合并到同一 burst。
3. 若平台确实保证单账号只会有一个有效 dialog，也仍建议保留 `conversation_key`，避免未来接入方变化时重新拆库。

### 0.2.6 burst 体验目标

对“小红书连续补发”场景，burst 的定义是：

1. 用户在较短时间内连续发送 2 到 N 条补充消息。
2. 这些消息构成同一波输入。
3. AI 应尽量等这一波收束后再回。
4. 若 AI 已开始处理，但这一波仍未结束，则尽量只保留最后一条有效回复。

推荐体验目标：

1. 用户连续发 3 到 5 条，最终只收到 1 条回复。
2. 用户刚补完最后一句后，首条有效回复不应明显超过 2 到 4 秒。
3. 用户不应连续看到“上一条回复刚发出，下一条更完整回复又来了”的机器人感。

### 0.2.7 session 状态模型（latest-wins 版）

建议 session 最小字段改为：

```json
{
  "conversation_key": "u123::d456",
  "profile_key": "u123",
  "version": 2,
  "state": "IDLE",
  "generation": 0,
  "last_ack_seq": 0,
  "max_enqueued_seq": 0,
  "last_enqueue_at_ms": 0,
  "first_enqueue_at_ms": 0,
  "debounce_until_ms": 0,
  "active_turn_id": "",
  "active_start_seq": 0,
  "active_end_seq": 0,
  "pending_turn_id": "",
  "pending_end_seq": 0,
  "pending_generation": 0,
  "fail_streak": 0,
  "updated_at_ms": 0
}
```

字段语义：

1. `last_ack_seq`
   - 不是“已经处理过的最后一条”。
   - 而是“已经被最终确认发送或确认静默提交的最后一条”。
2. `active_turn_id`
   - 当前正在生成的轮次。
3. `pending_turn_id`
   - 当前已经生成完成、等待发送或等待最终提交确认的候选轮次。
4. `pending_end_seq`
   - 当前候选轮次覆盖到哪一条消息。

强约束：

1. latest-wins 方案下，不得再把 `last_consumed_seq` 当作最终确认游标。
2. 只有最终获胜轮次完成提交后，才允许推进 `last_ack_seq`。

### 0.2.8 TurnDraft 模型（必须新增）

worker 生成完成后，不直接写最终 outbox 文本和最终业务状态，而是先产出 `TurnDraft`：

```json
{
  "turn_id": "t_xxx",
  "conversation_key": "u123::d456",
  "profile_key": "u123",
  "generation": 7,
  "covered_start_seq": 21,
  "covered_end_seq": 24,
  "dialog_id": "d456",
  "reply_text": "最终回复文本",
  "mutation_set": {
    "profile_patch": {},
    "user_state_patch": {},
    "history_appends": [],
    "recent_response_patch": {},
    "metrics_patch": {}
  },
  "created_at_ms": 0
}
```

`mutation_set` 的含义：

1. 当前轮次对画像的修改草稿
2. 当前轮次对用户状态的修改草稿
3. 当前轮次计划追加到历史的消息
4. 当前轮次计划更新的近期回复
5. 当前轮次需要记的业务指标

强约束：

1. `TurnDraft` 在 sender/finalizer 确认前不得提交到真实业务存储。
2. `TurnDraft` 必须支持按 `turn_id` 幂等提交。

### 0.2.9 TurnSandbox（必须新增）

为最小化对现有 ChatService 的侵入，本方案要求新增 `TurnSandbox`：

1. 允许 ChatService 正常读取真实画像与上下文。
2. 拦截本轮所有写操作：
   - `save_user_profile`
   - `save_user_state`
   - `add_message_to_history`
   - 其他对话状态写入
3. 将这些写操作收集为 `mutation_set`，而不是直接落库。

设计目的：

1. 保留现有 ChatService 的业务判断逻辑。
2. 避免为 latest-wins 全量重写业务层。
3. 把“生成结果”和“提交结果”明确分离。

### 0.2.10 入站流程（必须原子）

`enqueue_message()` 仍需一次事务完成：

1. dedupe 检查
2. dedupe 写入
3. seq 自增
4. 原文消息落库
5. session 更新
6. ready_users 调度
7. 返回 `{accepted, state, seq}`

与首版不同的点：

1. session 主键应改为 `conversation_key`
2. 普通消息只推进 `max_enqueued_seq`
3. `cancel_like` 额外执行 `generation += 1`
4. 生产环境不建议再依赖用户文案中的“好了/你回复吧”这类关键词做 `force_flush`
5. 若保留 `force_flush`，也只能作为调试能力，默认关闭，不得作为小红书正式体验主策略

### 0.2.11 worker 流程（latest-wins 版）

`run_user_turn(conversation_key)` 必须按以下顺序：

1. 获取会话锁
2. 读取 session
3. 若 `state != DEBOUNCING` 或尚未到点，则 reschedule 并退出
4. 以 `start_seq = last_ack_seq + 1`、`end_seq = max_enqueued_seq` 启动本轮
5. 将 session 置为 `RUNNING`
6. 读取 `start_seq ~ end_seq` 全部原文消息
7. 按顺序原文拼接
8. 在 `TurnSandbox` 中执行 ChatService，产出 `TurnDraft`
9. worker 完成后立即做**第一次 latest gate**
10. 若草稿仍是最新，则写候选 outbox；否则直接丢弃草稿
11. 根据 session 当前状态决定是否重新调度下一轮

### 0.2.12 第一次 latest gate（worker 侧）

worker 生成完成后，只要满足任一条件，就必须判定本轮失去发送资格：

1. `current_session.generation != draft.generation`
2. `current_session.max_enqueued_seq > draft.covered_end_seq`
3. `current_session.active_turn_id != draft.turn_id`

解释：

1. 第 1 条表示被 cancel/结束语义打断。
2. 第 2 条表示生成期间有更新消息进入，本轮已经不是“最新覆盖范围”。
3. 第 3 条表示当前执行权已被恢复流程或其他轮次替换。

处理动作：

1. 不发送旧回复
2. 不提交旧状态
3. 不推进 `last_ack_seq`
4. 若还有未确认消息，则重回 `DEBOUNCING`

### 0.2.13 候选 outbox 与发送前静默窗口

草稿通过 worker 侧 latest gate 后，不应立刻发送，而应进入候选 outbox：

1. 写入 `mq:outbox:{job_id}`
2. 记录：
   - `turn_id`
   - `generation`
   - `covered_end_seq`
   - `reply_text`
   - `dialog_id`
   - `mutation_set`
3. 将 `next_retry_at_ms` 设为 `now + MQ_PRE_SEND_SILENCE_MS`

`MQ_PRE_SEND_SILENCE_MS` 的目的：

1. 防止“刚生成完，用户又补一句”的临界误发
2. 让 sender 再观察一个极短窗口
3. 与主 debounce 分工不同，不能替代主 debounce

### 0.2.14 第二次 latest gate（sender/finalizer 侧）

sender 真正发送前，必须再次读取 session；满足任一条件即 drop：

1. `session.generation != job.generation`
2. `session.pending_turn_id != job.turn_id`（若采用 pending 标记）
3. `session.max_enqueued_seq > job.covered_end_seq`
4. `session.last_ack_seq >= job.covered_end_seq`

解释：

1. 第 1 条防 cancel。
2. 第 2 条防旧候选误发。
3. 第 3 条防普通补发覆盖旧草稿。
4. 第 4 条防重复发送或重复提交。

### 0.2.15 发送与提交顺序（必须固定）

最终顺序必须是：

1. sender 对通过 latest gate 的候选 job 调下游发送接口
2. 必须携带幂等键，建议 `client_msg_id = job_id`
3. 只有下游明确返回成功后，才进入 commit
4. commit `TurnDraft` 到真实业务存储
5. 原子推进 `last_ack_seq = covered_end_seq`
6. 清空 `pending_turn_id`
7. `mark_outbox_done(job_id)`

强约束：

1. 不得在发送前就提交真实业务状态。
2. 不得在发送失败时推进 `last_ack_seq`。
3. commit 必须按 `turn_id` 幂等。

### 0.2.16 空回复与业务静默

若当前轮次的最终业务结果是合法空回复：

1. 不发送 outbox 文本
2. 但仍需做一次 `silent commit`
3. 该 `silent commit` 仍需通过 latest gate
4. 成功后仍可推进 `last_ack_seq`

原因：

1. 有些业务轮次“静默”本身就是正确行为
2. 不能因为没有发文本，就让同一批消息永远处于未确认状态

### 0.2.17 失败与恢复

必须覆盖以下场景：

1. **worker 崩溃，draft 尚未产出**
   - `last_ack_seq` 未推进，恢复后重新生成
2. **worker 产出 draft，但尚未写 outbox 就崩溃**
   - draft 不视为已确认，恢复后可重算
3. **outbox 已写，但 sender 尚未发送**
   - 重启后从 outbox 恢复
4. **发送成功，但 commit 前进程崩溃**
   - 依赖下游幂等键重试发送，并补做 commit
5. **commit 成功，但 mark_outbox_done 前崩溃**
   - 依赖 `last_ack_seq >= covered_end_seq` 与 `turn_id` 幂等，防止重复提交与重复发送

### 0.2.18 默认参数建议（小红书基线）

推荐默认值：

```python
MQ_DEBOUNCE_MS = 1200
MQ_DEBOUNCE_APPEND_MS = 500
MQ_DEBOUNCE_MAX_MS = 2500
MQ_PRE_SEND_SILENCE_MS = 400
MQ_RUNNING_RECHECK_MS = 250
MQ_WORKER_POLL_MS = 100
MQ_SENDER_POLL_MS = 150
MQ_MAX_PENDING_MESSAGES = 30
MQ_OUTBOX_MAX_RETRIES = 8
MQ_RUNNING_STALE_AFTER_MS = 120000
MQ_SESSION_TTL_SECONDS = 604800
MQ_DEDUPE_TTL_SECONDS = 86400
```

调优原则：

1. debounce 用来接用户补发
2. pre-send silence 用来防临界误发
3. 两者都要短，但职责不同
4. 不建议把体验完全建立在“用户说了一个结束词就立即 flush”上

### 0.2.19 明确不做的事情

本方案明确不做：

1. 不在 MQ 层做 FAQ / 联系方式 / 收尾语义判断
2. 不在 MQ 层总结、压缩、改写用户原话
3. 不依赖用户文案中的“好了”“你回复吧”作为正式控制信号
4. 不要求真正中断底层 LLM socket
5. 不要求旧轮次一旦开始就必须发出去

唯一允许的狭义控制信号：

1. `cancel_like`
2. 且仅用于 `generation += 1`
3. 不得扩展为 FAQ / 顾虑 / 联系方式语义分流器

### 0.2.20 验收标准（latest-wins 专项）

以下全部通过，才算本节落地完成：

1. 用户 2 秒内连续发 3 到 5 条，最终只收到 1 条 AI 回复。
2. AI 生成中又补发普通消息，旧草稿不发送，最终只发覆盖最新输入的一条回复。
3. AI 生成中发送 cancel，旧草稿不发送，且不提交旧状态。
4. 合法空回复场景不发送文本，但能正确推进已确认游标。
5. 同一 `account_id` 下不同 `dialog_id` 不串队列。
6. send 成功后进程崩溃，重试不会导致用户侧重复可见回复。
7. worker 崩溃恢复后，不会重复推进电话/微信追问计数、不会重复写历史。
8. 历史、画像、近期回复等业务变更只由最终获胜 turn 提交一次。

### 0.2.21 建议改造文件范围

本节落地时，建议至少涉及：

- 需要升级：
  - `src/services/queue/message_models.py`
  - `src/services/queue/queue_store.py`
  - `src/services/queue/message_orchestrator.py`
  - `src/workers/reply_sender_worker.py`
  - `src/modules/conversation/application/process_chat_turn.py`

- 建议新增：
  - `src/services/queue/turn_draft_models.py`
  - `src/services/queue/turn_sandbox.py`
  - `src/services/queue/turn_commit_service.py`

交付顺序建议：

1. 先把 `account_id` 主键升级为 `conversation_key`
2. 再引入 `last_ack_seq / pending_turn_id / covered_end_seq`
3. 再拆出 `TurnDraft + TurnSandbox + TurnCommit`
4. 最后把 sender 切为“发送 + commit finalizer”

## 零点一、2026-04-06 最终优化约束（职责边界收敛版）

> 本节是在 `零、2026-03-18 最终实施基线` 之上的补充强约束。  
> 若与 `零点二` 冲突，以 `零点二` 为准；其余冲突再以本节为准。  
> 目的：在不影响真人感、不影响资料收集逻辑的前提下，继续使用 MQ 方案。

### 0.1.1 总原则

MQ 必须严格定位为**消息编排层**，不能演化为**业务语义决策层**。

目标必须同时满足：

1. 不影响真人感与接话节奏。
2. 不改变现有资料收集、联系方式、FAQ、收尾逻辑。
3. 不让用户明显等待过久。
4. 不丢消息、不乱序、不误发 stale 回复。

一句话要求：

- MQ 只改**时序**
- ChatService 只改**语义**
- LLM 只改**表达**

### 0.1.2 MQ 职责边界（强约束）

MQ 只允许负责以下事项：

1. 接消息
2. 排序
3. 防抖
4. 合并
5. 丢弃 stale 回复
6. 异步投递
7. 去重
8. 重试
9. 恢复
10. 可观测性

MQ 明确**不允许**负责以下事项：

1. 用户意图识别
2. FAQ / 顾虑判断
3. ask_field 决策
4. 联系方式推进逻辑
5. 收尾判定
6. 字段提取
7. 资料收集顺序
8. 话术选择
9. prompt 选择
10. 任意业务规则改写

### 0.1.3 与 ChatService 的契约

MQ 与业务层的边界必须明确：

- MQ 保证：
  1. 消息不丢
  2. 顺序正确
  3. stale 回复不下发
  4. 投递可恢复

- ChatService 保证：
  1. 资料收集逻辑
  2. FAQ 优先
  3. 联系方式逻辑
  4. 收尾逻辑
  5. 真人感和话术风格

强约束：

1. MQ 不得依据“这是 FAQ / 联系方式 / 收尾 / 取消”做语义分流。
2. MQ 不得改变 `ChatService.process_chat_request()` 的业务语义入口。
3. MQ 不得自行改写用户原话。

### 0.1.4 消息合并规则（必须保守）

为了不伤真人感和资料收集逻辑，消息合并仅允许做**原文拼接**：

1. 按时间顺序拼接
2. 保留换行
3. 不摘要
4. 不压缩语义
5. 不重写
6. 不替用户“整理表达”

允许：

```text
深圳
IT
5万
```

禁止：

```text
我在深圳，做IT，月薪5万
```

后一种属于 MQ 越界做语义加工，视为不符合本方案。

### 0.1.5 stale 判定必须双保险

为了彻底避免旧回复误发，stale 判定必须至少做两次：

1. worker 生成完成、写 outbox 前检查一次
2. sender 真正发送前再检查一次

任何仅在 worker 判 stale、sender 不复核的实现，都视为仍有误发风险。

### 0.1.6 时延优化原则（不改业务逻辑版）

优先优化工程层，不优先修改业务语义层：

1. debounce
2. worker poll
3. sender poll
4. timeout / retry
5. recovery / backpressure

默认建议范围：

```python
MQ_DEBOUNCE_MS = 300 ~ 500
MQ_DEBOUNCE_APPEND_MS = 150 ~ 300
MQ_DEBOUNCE_MAX_MS = 800 ~ 1200
```

原则：

1. 能接住用户紧跟着补发的消息
2. 又不能为了“多攒几条消息”而明显拖慢首轮响应

### 0.1.7 高风险场景保护

以下场景必须优先保护现有业务逻辑，不允许因为 MQ 合并或调度变化而改变语义：

1. FAQ / 顾虑答疑
2. 联系方式追问与拒绝
3. 收尾轮
4. already_ended 轮
5. 纠错轮
6. resume 主线轮

要求：

1. MQ 只能保证时序和不丢消息
2. 不得改变上述场景的业务判断结果

### 0.1.8 验收新增红线

除原有 MQ 验收外，新增以下红线：

1. 不能因 MQ 改造导致真人感明显下降。
2. 不能因 MQ 改造导致资料收集 ask_field、FAQ 优先、联系方式逻辑、收尾逻辑漂移。
3. 不能因 MQ 合并导致用户补充信息被错误改写。
4. 不能因 stale 丢弃导致旧回复仍被 sender 发出。

建议新增回归范围：

1. FAQ 打断主线
2. 联系方式拒绝后继续主线
3. 收尾补触发
4. already_ended 下继续答疑
5. 多条补充消息合并后的字段提取一致性

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

首版语义澄清：

- `RUNNING` 期间收到**普通补发消息**时，不提升 `generation`，也**不要求**把当前 turn 判成 stale。
- 当前 turn 可以正常完成并投递；worker 在 `finish_turn_success()` 后基于 `dirty=true` 触发下一轮。
- 只有 `cancel / 结束 / 反悔` 这类消息才通过 `generation += 1` 让旧 turn 回复 stale drop。

### 0.4.1 后续真人化增强方案（暂不纳入本轮实现）

> 本节是后续优化方向，当前版本**只记录方案，不实现、不改变 0.4 首版语义**。  
> 目的：在后续阶段进一步减少“用户连续补发多条消息后收到多条 AI 回复”的机器人感。

当前首版语义的取舍是：

- 优先保证不丢消息、不乱序、不误发明显 stale 回复
- `RUNNING + 普通补发消息` 仍允许当前 turn 先完成并投递
- 因此在 AI 单轮耗时较长时，用户可能先后收到 2 条甚至更多回复

这在工程正确性上可接受，但在“像真人聊天”目标下，仍有优化空间。后续建议采用更偏 `latest-wins` 的交付策略：

1. **生成可失效**
   - 当 turn 处于 `RUNNING` 时，只要用户又发送了新的**普通补发消息**，当前 turn 进入“可失效候选”状态。
   - 当前 turn 可以继续生成完成，但默认不再保证一定下发。

2. **发送前静默窗口**
   - AI 生成完成后不立刻发送，而是先进入一个很短的发送前静默窗口。
   - 该窗口的目的不是等待用户完整打字，而是防止“刚生成完就有新消息补进来”。
   - 该窗口建议明显短于主 debounce，例如：

```python
MQ_PRE_SEND_SILENCE_MS = 300 ~ 800
```

3. **主输入合并窗口仍然单独存在**
   - 如果目标是更像真人地“等用户把一句话补完”，不能只依赖发送前静默窗口。
   - 主 debounce 仍应作为“等待用户继续补发”的主窗口，量级可以比发送前静默窗口更长。
   - 对小红书这类连发明显的平台，后续可优先考虑：

```python
MQ_DEBOUNCE_MS = 1200 ~ 2000
MQ_DEBOUNCE_MAX_MS = 2500 ~ 4000
```

4. **最终尽量只发最新一条**
   - 若当前 turn 生成完成时已经确认有更新的普通消息到达，且这条回复尚未真正发送，则允许直接丢弃当前 turn 的未发送回复。
   - 系统内部可以重算多次，但用户侧尽量只看到基于最新上下文的最后一条回复。

5. **适用前提**
   - 该方案只适用于“真人感优先”的聊天场景。
   - 代价是会增加部分已生成但未发送回复的 token 浪费，也会增加状态控制复杂度。

6. **实施边界**
   - 该方案属于后续体验升级，不属于本轮 P0/P1/P2 的必须项。
   - 真正实施时，需要同步收紧以下约束：
     1. worker 侧增加“普通补发消息导致当前回复可失效”的判定
     2. sender 侧增加发送前静默窗口和最新 generation 再确认
     3. 文档中的首版语义、验收口径、真实回归脚本需一并更新

一句话总结：

- **当前首版方案**：先保证稳，允许普通补发后用户收到多条回复
- **后续真人化方案**：内部可多轮计算，但用户侧尽量只看到最新一条回复

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
   这里指普通补发消息默认遵循 `RUNNING + dirty=true` 语义：当前轮可先完成，随后再跑下一轮；并不要求普通补发也 stale 掉当前轮。
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
