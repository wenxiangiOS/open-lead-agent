# 外部接入指南（同步 Chat + 异步 MQ 双模式）

更新时间：2026-03-19

本文档说明本项目对外暴露的两种接入方式：

1. 同步模式：`POST /api/doubao/chat`
2. 异步模式：`POST /api/xiaohongshu/messages/ingest` + 回调或轮询取回复

两种模式可同时保留，按你的外部系统能力选择。

## 1. 总体架构

### 1.1 同步模式（请求即响应）

外部系统 -> `/api/doubao/chat` -> 本服务处理 AI -> HTTP 响应直接返回 AI 文本

特点：
- 接入简单
- 外部无需消息队列
- 外部请求会等待 AI 完成（受 AI 耗时影响）

### 1.2 异步模式（入站与出站解耦）

外部系统 -> `/api/xiaohongshu/messages/ingest`（快速 ack）-> 本服务队列+worker 异步处理 -> 回调外部接口（`XHS_REPLY_API`）或外部轮询 `/api/xiaohongshu/messages/replies`

特点：
- 高并发下更稳
- 支持消息聚合、去重、重试、背压
- 对外平台可“先收后发”

## 2. 何时选哪种模式

### 2.1 推荐同步模式的场景

- 外部平台本身就是“用户发一条，立即等一条回复”
- QPS 不高
- 无需复杂重试/排队治理

### 2.2 推荐异步模式的场景

- 外部平台回调入口必须快速返回，不可长时间阻塞
- 用户可能连续多条消息
- 需要削峰填谷、失败重试、去重、幂等等能力

## 3. 同步模式接入（`/api/doubao/chat`）

### 3.1 接口定义

- 方法：`POST`
- 路径：`/api/doubao/chat`
- Content-Type：`application/json`

请求体（核心字段）：

```json
{
  "question": "你好，我在深圳，95后",
  "accountId": "user_10001",
  "dialogId": "dlg_001",
  "sex": "女",
  "timestamp": "2026-03-19T10:20:30+08:00"
}
```

字段说明：
- `question`：用户输入文本（必填）
- `accountId`：用户唯一标识（必填）
- `dialogId`：会话标识（可选，建议传）
- `sex`：`男/女/other/unknown`（可选）
- `timestamp`：ISO 时间（可选）

响应体（典型）：

```json
{
  "success": true,
  "response": "你好呀～先简单说说你现在大概多大呢？",
  "dialogId": "dlg_001",
  "timestamp": "2026-03-19T10:20:31.123456",
  "error": null,
  "confidence": null,
  "debug_info": null
}
```

### 3.2 调用示例（curl）

```bash
curl -X POST "http://127.0.0.1:8000/api/doubao/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question":"我是95后，在深圳",
    "accountId":"user_10001",
    "dialogId":"dlg_001",
    "sex":"女",
    "timestamp":"2026-03-19T10:20:30+08:00"
  }'
```

### 3.3 外部系统接入步骤

1. 生成并持久化 `accountId`（同一用户必须稳定不变）。
2. 每条消息调用 `/api/doubao/chat`。
3. 将响应中的 `response` 展示给用户。
4. 将请求与响应一起落日志，便于回溯。
5. 对 5xx/超时做有限重试（建议最多 1~2 次）。

## 4. 异步模式接入（`/api/xiaohongshu/messages/ingest`）

### 4.1 入站接口定义

- 方法：`POST`
- 路径：`/api/xiaohongshu/messages/ingest`
- Content-Type：`application/json`

请求体：

```json
{
  "accountId": "user_10001",
  "dialogId": "dlg_001",
  "message": "我在深圳，95后",
  "platformMsgId": "xhs_msg_987654321",
  "timestamp": "2026-03-19T10:30:00+08:00",
  "sex": "女"
}
```

关键约束：
- `platformMsgId` 必须由外部平台保证唯一（用于去重）。
- `accountId` 必须稳定（用于用户级排队与上下文）。

入站响应（典型）：

```json
{
  "success": true,
  "accepted": true,
  "status": "queued",
  "sessionState": "DEBOUNCING",
  "seq": 12,
  "pending": 3,
  "maxPending": 20,
  "cancelLike": false,
  "forceFlush": false
}
```

常见 `status`：
- `queued`：入队成功
- `duplicate`：重复消息（同 `platformMsgId`）
- `queue_full`：触发背压
- `ignored_empty`：空消息
- `invalid_payload`：关键字段缺失

### 4.2 出站回调（本服务 -> 外部）

当 worker 产出回复后，本服务会调用 `XHS_REPLY_API`（可配置备份 `XHS_REPLY_API_BACKUP`）。

发送载荷：

```json
{
  "accountId": "user_10001",
  "dialogId": "dlg_001",
  "message": "好的呀～我先记下啦，那你现在做什么工作的呀？",
  "clientMsgId": "job_id_xxx"
}
```

`clientMsgId` 是幂等键（建议外部按此去重）。

### 4.3 轮询取回复（可选）

如果外部暂时不做回调接收，可轮询：

- 方法：`GET`
- 路径：`/api/xiaohongshu/messages/replies`
- 参数：
  - `accountId` 必填
  - `after` 已消费游标（默认 0）
  - `limit` 每次条数（1~100）

示例：

```bash
curl "http://127.0.0.1:8000/api/xiaohongshu/messages/replies?accountId=user_10001&after=0&limit=20"
```

响应示例：

```json
{
  "success": true,
  "accountId": "user_10001",
  "after": 0,
  "nextAfter": 25,
  "replies": [
    {
      "id": 25,
      "turn_id": "turn_xxx",
      "message": "你好呀～先简单说说你现在多大呢？",
      "dialogId": "dlg_001",
      "timestamp": 1773897600000
    }
  ]
}
```

### 4.4 外部系统接入步骤（异步）

1. 外部消息到达时，立即调用 `ingest`。
2. 处理 `accepted/status`：
   - `queued/duplicate` 视为成功 ack。
   - `queue_full` 按外部策略降级或延迟重试。
3. 选择回包方式：
   - 推荐：接收本服务回调（`XHS_REPLY_API`）。
   - 备选：定时轮询 `replies`。
4. 用 `clientMsgId`（回调）或 `id`（轮询）做幂等消费。
5. 记录全链路日志：`platformMsgId -> seq -> replyId/clientMsgId`。

## 5. 安全与鉴权

### 5.1 ingest 鉴权（可选）

支持两种防护（可同时开）：

1. API Key
   - 环境变量：`XHS_INGEST_API_KEY`
   - 请求头：`X-API-Key: <key>`

2. HMAC 签名
   - 环境变量：`XHS_INGEST_SIGNING_SECRET`
   - 请求头：
     - `X-Timestamp`
     - `X-Signature`
   - 签名规则：`HMAC_SHA256(secret, "<timestamp>.<raw_body>")`

建议生产环境至少开启一种，优先 API Key + HMAC 双开。

### 5.2 网络建议

- 对外入口加 WAF/反向代理限流。
- 仅放行可信来源 IP（如可行）。
- 所有外部调用使用 HTTPS。

## 6. 关键配置项（双模式相关）

### 6.1 通用

- `MQ_ENABLED`
  - `true`：启用异步 worker 链路
  - `false`：关闭异步 worker（同步 `/api/doubao/chat` 仍可用）

### 6.2 异步入站/处理

- `MQ_MAX_PENDING_MESSAGES`：单用户最大积压（背压阈值）
- `MQ_DEBOUNCE_MS` / `MQ_DEBOUNCE_APPEND_MS` / `MQ_DEBOUNCE_MAX_MS`：消息聚合窗口
- `MQ_READY_BATCH_SIZE` / `MQ_WORKER_POLL_MS`：worker 调度节奏

### 6.3 异步出站

- `XHS_REPLY_API`：主回调地址
- `XHS_REPLY_API_BACKUP`：备回调地址
- `XHS_REPLY_TIMEOUT_SECONDS`：回调超时
- `MQ_OUTBOX_MAX_RETRIES`：失败重试次数
- `MQ_SENDER_POLL_MS`：sender 轮询间隔

## 7. 错误处理与重试建议（外部系统）

### 7.1 同步模式

- `422`：请求参数错误，不重试，修正请求。
- `500`：服务异常，可短重试。
- 超时：建议 1~2 次指数退避重试。

### 7.2 异步模式

- ingest 返回 `queued/duplicate`：视为外部投递成功。
- ingest 返回 `queue_full`：延迟重试并上报告警。
- 回调接收端：必须幂等，且能容忍重复投递。

## 8. 本地联调清单

1. 启动服务：`python3 main.py`
2. 同步模式冒烟：调用 `/api/doubao/chat`
3. 异步模式冒烟：
   - 调 `ingest`
   - 看是否产生回调，或轮询 `replies`
4. 检查健康与指标：
   - `/health`
   - `/api/doubao/stats`（查看 `message_queue` 指标）

## 9. 示例代码与参考文件

- 同步调用示例：
  - `examples/chat_api_example.py`
- 异步入站示例：
  - `examples/xhs_ingest_example.py`
- 异步轮询示例：
  - `examples/xhs_replies_example.py`
- 设计与运行手册：
  - `docs/message_queue_design.md`
  - `docs/message_queue_runbook.md`

## 10. 常见接入方案建议

### 方案 A：先快速上线（推荐起步）

1. 先接 `/api/doubao/chat`。
2. 跑通后再逐步迁移到 ingest 异步链路。

### 方案 B：平台回调严格限时（推荐直接异步）

1. 外部平台收到用户消息后立刻 `ingest`。
2. 外部平台暴露接收回调接口给 `XHS_REPLY_API`。
3. 外部平台按 `clientMsgId` 做幂等落库。

### 方案 C：没有回调接收能力

1. 继续用 `ingest` 入站。
2. 用 `replies` 轮询拉取结果。

## 10.1 关于“同一种调用方式是否可同时调用两种模式”

结论：服务端可以同时保留两种模式，但外部不能用完全同一份请求协议直接同时打这两个接口。

原因：

1. 路径不同：`/api/doubao/chat` vs `/api/xiaohongshu/messages/ingest`
2. 请求字段不同：`question` vs `message/platformMsgId`
3. 响应语义不同：同步直接返回 AI 文本；异步只返回入队状态，结果稍后回调或轮询

如果外部希望“看起来是一种调用方式”，建议在外部增加一层适配器/网关：

1. 外部上游只调用统一协议
2. 适配器按配置路由到同步或异步接口
3. 适配器将两种返回格式统一成外部标准格式

当前项目建议：生产默认走异步模式，同步模式保留为调试和回退链路。

## 11. 迁移说明（从单模式到双模式）

如果你历史上只用了 `/api/doubao/chat`，建议迁移顺序：

1. 保持同步模式不动，新增异步链路联调环境。
2. 小流量切到 `ingest`，观察：
   - `ingest_accepted`
   - `turn_succeeded`
   - `outbox_delivery_success`
3. 稳定后扩大异步流量。
4. 同步模式保留为应急回退链路。
