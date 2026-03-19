# 外部接入一页清单（Quick Start）

更新时间：2026-03-19

适用对象：第三方联调同学、实施同学。  
完整说明请看：`docs/external_integration_guide.md`。

## 1. 先选模式

1. 要“请求后立刻拿回复” -> 用同步模式：`/api/doubao/chat`
2. 要“快速 ack + 后台处理 + 回调/轮询” -> 用异步模式：`/api/xiaohongshu/messages/ingest`

注意：

- 两种模式可同时保留，但不是同一个接口协议。
- 如果外部想统一成一种调用方式，需要在外部加适配层做字段与返回格式转换。

---

## 2. 同步模式最小接入

### 2.1 请求

`POST /api/doubao/chat`

```json
{
  "question": "我是95后，在深圳",
  "accountId": "user_10001",
  "dialogId": "dlg_001",
  "sex": "女",
  "timestamp": "2026-03-19T10:20:30+08:00"
}
```

### 2.2 你要做的事

1. 给每个用户生成稳定 `accountId`
2. 每条消息调用一次接口
3. 把响应里的 `response` 直接展示给用户
4. 失败重试最多 1~2 次（仅 5xx/超时）

### 2.3 curl

```bash
curl -X POST "http://127.0.0.1:8000/api/doubao/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question":"我是95后，在深圳",
    "accountId":"user_10001",
    "dialogId":"dlg_001",
    "sex":"女"
  }'
```

---

## 3. 异步模式最小接入

### 3.1 入站请求

`POST /api/xiaohongshu/messages/ingest`

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

### 3.2 入站返回判断

1. `queued` / `duplicate`：当成功处理
2. `queue_full`：延迟重试
3. `invalid_payload`：修请求参数

### 3.3 出站回包（推荐）

你提供回调地址给 `XHS_REPLY_API`，本服务会推送：

```json
{
  "accountId": "user_10001",
  "dialogId": "dlg_001",
  "message": "好的呀～那你现在做什么工作呢？",
  "clientMsgId": "job_id_xxx"
}
```

你要按 `clientMsgId` 做幂等去重。

### 3.4 没有回调能力时（备选）

轮询：

`GET /api/xiaohongshu/messages/replies?accountId=user_10001&after=0&limit=20`

用返回中的 `id` 或 `nextAfter` 做游标推进。

---

## 4. 上线前必查 8 项

1. `accountId` 是否稳定
2. `platformMsgId` 是否全局唯一（异步）
3. 外部是否做幂等（`clientMsgId`）
4. 是否有 5xx/超时重试策略
5. 是否记录请求+响应日志
6. 是否配置 HTTPS
7. 是否开启 ingest 鉴权（API Key 或签名）
8. 是否有回退方案（同步模式保底）

---

## 5. 常用联调命令

```bash
# 健康检查
curl "http://127.0.0.1:8000/health"

# 同步模式
curl -X POST "http://127.0.0.1:8000/api/doubao/chat" -H "Content-Type: application/json" -d '{"question":"你好","accountId":"u1"}'

# 异步入站
curl -X POST "http://127.0.0.1:8000/api/xiaohongshu/messages/ingest" -H "Content-Type: application/json" -d '{"accountId":"u1","message":"你好","platformMsgId":"m1"}'

# 异步轮询
curl "http://127.0.0.1:8000/api/xiaohongshu/messages/replies?accountId=u1&after=0&limit=20"
```
