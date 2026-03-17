# Message Queue Implementation Tasks

> 创建时间：2026-03-17
> 目标读者：负责按文档直接编码实现的其他模型或工程师
> 依赖文档：`docs/message_queue_design.md`

## 一、使用说明

本任务书用于指导按阶段实现消息队列编排能力。

实现时必须遵守：

1. 先阅读 `docs/message_queue_design.md`
2. 严格按本任务书阶段顺序实施
3. 每阶段只做该阶段要求的内容，不擅自扩 scope
4. 不要重写现有 `ChatService` 业务逻辑
5. 不要把消息队列、worker、outbox 逻辑塞进 `ChatService`

本任务书默认：

- 现有 `ChatService.process_chat_request()` 作为单轮对话引擎继续保留
- Redis 为主状态存储
- 首版只落 3 个状态：`IDLE`、`DEBOUNCING`、`RUNNING`
- “待下一轮”只用 `RUNNING + dirty=true` 表示

## 二、总目标

实现一套异步消息编排链路，满足：

1. 连续短消息自动合并
2. AI 处理中允许继续发消息
3. 用户“算了/不聊了”后旧回复失效
4. 回复通过 outbox 异步投递
5. 可在多实例场景下保持单用户串行

## 三、实现边界

### 3.1 可以新增

- `src/services/queue/message_models.py`
- `src/services/queue/intent_classifier.py`
- `src/services/queue/queue_store.py`
- `src/services/queue/message_orchestrator.py`
- `src/services/queue/reply_delivery_service.py`
- `src/workers/message_queue_worker.py`
- `src/workers/reply_sender_worker.py`
- 与上述功能相关的测试文件
- 必要的 settings 配置项
- 必要的 API 路由

### 3.2 可以小改

- `src/api/app.py`
- `src/api/routes/`
- `src/config/settings.py`

前提：

- 仅为注册新路由、初始化新服务、增加配置项
- 不破坏现有同步聊天链路

### 3.3 不要改

- `ChatService` 核心业务流程
- 现有资料收集策略
- 现有 AI prompt 主逻辑
- 现有用户画像字段语义

除非出现明确编译错误或必须的接线修改。

## 四、阶段划分

按以下顺序实现：

1. Phase 1: 数据模型、意图分类、Redis 存储层
2. Phase 2: 编排器和入站 ingest 路由
3. Phase 3: 消费 worker
4. Phase 4: outbox 投递和 sender worker
5. Phase 5: 测试和验收

不要跳阶段。

## 五、Phase 1

### 5.1 目标

建立最小可用的队列基础层，包括：

- 数据模型
- cancel/force_flush 规则分类
- Redis key 读写
- session / msg / dedupe / ready_users / outbox 的基础操作

### 5.2 必做文件

- `src/services/queue/message_models.py`
- `src/services/queue/intent_classifier.py`
- `src/services/queue/queue_store.py`

### 5.3 必做内容

#### A. `message_models.py`

实现以下 dataclass：

- `IncomingMessage`
- `QueueSession`
- `TurnContext`
- `OutboxJob`
- `EnqueueResult`

字段以 `docs/message_queue_design.md` 为准。

#### B. `intent_classifier.py`

实现：

```python
class QueueIntentClassifier:
    def classify(self, content: str) -> dict:
        ...
```

返回格式固定：

```python
{
    "cancel_like": bool,
    "force_flush": bool,
}
```

首版仅做规则匹配，不调用大模型。

#### C. `queue_store.py`

实现以下公开方法：

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

### 5.4 实现要求

- Redis key 命名必须与设计文档一致
- 所有 JSON 统一 `json.dumps(..., ensure_ascii=False)`
- `enqueue_message()` 必须原子
- session 和 msg 要设置 TTL
- 空 session 要自动返回默认值

### 5.5 Phase 1 完成标准

满足以下条件：

1. 可以把消息入队到 Redis
2. session 能正确从 `IDLE` 进入 `DEBOUNCING`
3. dedupe 生效
4. ready_users 中能看到被调度的 user
5. start_turn 能生成 `TurnContext`

### 5.6 Phase 1 禁止事项

- 不要接 `ChatService`
- 不要写 worker
- 不要写小红书发送逻辑

## 六、Phase 2

### 6.1 目标

在不破坏现有同步接口的前提下，增加异步 ingest 能力，并将 Redis 存储层接成一个完整编排入口。

### 6.2 必做文件

- `src/services/queue/message_orchestrator.py`
- 新增或修改 `src/api/routes/` 中的小红书 ingest 路由
- 必要时更新 `src/api/app.py`

### 6.3 必做内容

#### A. `message_orchestrator.py`

实现：

```python
class MessageOrchestrator:
    async def ingest(self, payload: dict) -> dict: ...
    async def run_user_turn(self, account_id: str) -> None: ...
```

本阶段先实现 `ingest()`，`run_user_turn()` 可以写空壳或最小逻辑，完整逻辑在 Phase 3 完成。

#### B. ingest 路由

新增：

`POST /api/xiaohongshu/messages/ingest`

请求示例：

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

响应示例：

```json
{
  "success": true,
  "accepted": true,
  "status": "queued"
}
```

### 6.4 `ingest()` 详细要求

`ingest()` 必须完成：

1. 参数校验
2. 内容去空白
3. 调用 `QueueIntentClassifier`
4. 组装 `IncomingMessage`
5. 调用 `queue_store.enqueue_message`
6. 返回标准响应

### 6.5 响应规范

支持以下状态：

- `queued`
- `duplicate`
- `ignored_empty`
- `invalid_request`

### 6.6 Phase 2 完成标准

满足以下条件：

1. HTTP 请求可以成功入队
2. duplicate 请求不会重复入队
3. 空消息返回 `ignored_empty`
4. 现有 `/api/doubao/chat` 不受影响

### 6.7 Phase 2 禁止事项

- 不要实现 worker 常驻循环
- 不要在 ingest 接口里同步调用 `ChatService`
- 不要把 ingest 改成同步返回 AI 文本

## 七、Phase 3

### 7.1 目标

实现消费 worker，让到期消息真正进入 `ChatService` 处理。

### 7.2 必做文件

- `src/workers/message_queue_worker.py`
- 完善 `src/services/queue/message_orchestrator.py`

### 7.3 必做内容

#### A. `message_queue_worker.py`

实现常驻循环：

1. 拉取 `ready_users`
2. 遍历调用 `orchestrator.run_user_turn(account_id)`
3. 捕获异常并记录日志
4. 空闲时 sleep

#### B. `run_user_turn(account_id)`

必须严格按以下步骤：

1. 获取用户级分布式锁
2. 读取 session
3. 条件不满足则 reschedule 后退出
4. 调用 `start_turn`
5. 读取 turn 对应消息
6. 按顺序拼接文本
7. 构造 `ChatRequest`
8. 调用 `chat_service.process_chat_request`
9. 二次读取 session 判断 stale
10. stale 则 `mark_turn_stale`
11. 非 stale 且有回复则写 outbox
12. `finish_turn_success`

### 7.4 重要要求

- 严禁直接在 worker 里拼写 Redis key 操作，统一走 `QueueStore`
- 拼接消息时不能改写原文
- `result["response"] == ""` 不是异常
- worker 异常时不能推进 `last_consumed_seq`

### 7.5 Phase 3 完成标准

满足以下条件：

1. ready_users 到时后会触发真实处理
2. 多条短消息只会调用一次 `ChatService`
3. `RUNNING` 期间来新消息会触发下一轮
4. cancel 消息会让旧 turn stale

### 7.6 Phase 3 禁止事项

- 不要直接发送小红书消息
- 不要在这里实现 outbox 重试逻辑

## 八、Phase 4

### 8.1 目标

实现 outbox 投递链路，保证 AI 结果可靠下发。

### 8.2 必做文件

- `src/services/queue/reply_delivery_service.py`
- `src/workers/reply_sender_worker.py`

### 8.3 必做内容

#### A. `reply_delivery_service.py`

实现：

```python
class ReplyDeliveryService:
    async def send_reply(self, account_id: str, reply_text: str, dialog_id: str | None = None) -> None:
        ...
```

此类只负责：

- 调用小红书发送接口
- 抛出异常或返回成功

不要在这里做 outbox 状态管理。

#### B. `reply_sender_worker.py`

实现常驻循环：

1. 拉取 `fetch_due_outbox_jobs`
2. 调用 `ReplyDeliveryService.send_reply`
3. 成功则 `mark_outbox_done`
4. 失败则 `retry_outbox`

### 8.4 重试规则

必须使用设计文档中的指数退避策略。

### 8.5 Phase 4 完成标准

满足以下条件：

1. worker 能消费 outbox
2. 成功时 job 被移除
3. 失败时 job 会重试
4. 达到上限后不再无限重试

### 8.6 Phase 4 禁止事项

- 不要把发送逻辑写回 `MessageOrchestrator`
- 不要把 Redis job 状态更新写进 `ReplyDeliveryService`

## 九、Phase 5

### 9.1 目标

补齐测试、恢复逻辑、启动接线和验收。

### 9.2 必做测试

新增或补齐：

- `tests/unit/test_queue_intent_classifier.py`
- `tests/unit/test_queue_store.py`
- `tests/unit/test_message_orchestrator.py`
- `tests/unit/test_reply_sender_worker.py`
- 必要的集成测试

### 9.3 必测场景

1. 连发 4 条短消息，只触发 1 次 AI 调用
2. AI 处理中再发消息，旧轮后接新轮
3. AI 处理中发“算了”，旧轮结果被丢弃
4. duplicate 平台回调不会重复处理
5. outbox 失败后会重试
6. 空回复不发送但轮次正常结束
7. stale running session 可以恢复

### 9.4 恢复逻辑

需要在 worker 启动时或定时任务中执行：

```python
queue_store.recover_stale_running_sessions(...)
```

### 9.5 Phase 5 完成标准

满足以下条件：

1. 所有单测通过
2. 至少一组集成测试通过
3. worker 启动后可自动恢复异常 `RUNNING` session
4. 系统日志能覆盖关键节点

## 十、任务顺序要求

实现顺序必须是：

1. 先完成 Phase 1 并自测
2. 再做 Phase 2
3. 再做 Phase 3
4. 再做 Phase 4
5. 最后做 Phase 5

不要边写 worker 边补存储层。

## 十一、统一开发约束

### 11.1 代码风格

- 优先复用项目现有 logging 风格
- 不新增无必要的框架
- 不引入新的外部队列中间件
- 首版只用 Redis

### 11.2 架构约束

- `QueueStore` 只做存储，不做业务编排
- `MessageOrchestrator` 做编排，不直接散落 Redis 操作
- `ReplyDeliveryService` 只做发送，不管理 job 状态
- worker 只负责循环和调度

### 11.3 风险约束

- 不要使用进程内 dict 保存会话主状态
- 不要试图真正 cancel 正在运行的模型请求
- 不要在队列层再调用一层大模型做总结
- 不要修改现有 `ChatService` 的业务判定顺序

## 十二、每阶段交付格式

每完成一个 Phase，提交结果时应包含：

1. 改动文件列表
2. 实现了哪些接口
3. 没实现的部分
4. 本阶段测试结果
5. 已知风险

示例格式：

```text
Phase 2 完成

Changed Files:
- src/services/queue/message_orchestrator.py
- src/api/routes/xiaohongshu_ingest.py
- src/api/app.py

Implemented:
- MessageOrchestrator.ingest
- POST /api/xiaohongshu/messages/ingest

Not Implemented Yet:
- run_user_turn full logic
- workers

Tests:
- unit tests for ingest passed

Risks:
- worker not wired yet
```

## 十三、最终验收标准

全部实现完成后，必须满足：

1. 用户连续发送多条短消息时，只触发合并后的轮次处理
2. AI 处理中收到新消息时，新消息不会丢
3. 用户发“算了/不用了”后，旧回复不会再下发
4. 小红书回调重复到达时不会重复回复
5. 回复发送失败时会按 outbox 重试
6. Redis 不会无限堆积垃圾 key
7. 现有同步测试接口仍能正常工作

## 十四、给实现模型的最后提醒

最容易做错的地方只有 5 个：

1. 把队列逻辑塞进 `ChatService`
2. 不做 outbox，直接在 worker 里发消息
3. 不做 generation，导致“算了”后旧回复照发
4. 用进程内内存保存 session
5. worker 异常后错误推进 `last_consumed_seq`

只要避开这 5 个问题，实现方向基本不会错。
