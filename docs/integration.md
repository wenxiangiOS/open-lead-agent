# 接入指南 / Integration Guide

这份文档面向想把 `open-lead-agent` 接到自己系统里的开发者或集成方。

你不需要理解项目内部所有模块。最小接入只需要调用一个接口：

```text
POST /api/chat
```

## 1. 基本流程

```text
用户发消息
  -> 你的系统收到消息
  -> 转成 open-lead-agent 的请求格式
  -> 调用 /api/chat
  -> 把 response 返回给用户
```

例如：

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "user-001",
    "dialogId": "dialog-001",
    "question": "你好，我想了解一下",
    "profile": {}
  }'
```

## 2. 请求格式

```json
{
  "accountId": "user-001",
  "dialogId": "dialog-001",
  "question": "你好，我想了解一下",
  "profile": {
    "location": "深圳"
  }
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `accountId` | 是 | 用户唯一 ID。用于识别同一个用户。 |
| `dialogId` | 否 | 会话 ID。用于区分同一用户的不同咨询会话。 |
| `question` | 是 | 用户本轮输入的消息。 |
| `profile` | 否 | 接入方已知的用户资料，比如城市、手机号、学历等。 |

## 3. accountId 怎么传

`accountId` 是用户唯一标识。

不同渠道可以这样映射：

| 渠道 | 推荐 accountId |
| --- | --- |
| 网站聊天窗口 | 登录用户 ID 或 visitorId |
| 微信公众号 | openid |
| 企业微信 | external_userid |
| 飞书 | open_id |
| App | app user id |
| CRM | lead id 或 customer id |

要求：

- 同一个用户每次传同一个 `accountId`
- 不要传用户手机号、身份证号等敏感信息作为 `accountId`
- 如果没有登录用户，可以生成一个匿名 visitor id

## 4. dialogId 怎么传

`dialogId` 表示一次会话或一次咨询。

推荐规则：

| 场景 | 推荐 dialogId |
| --- | --- |
| 一个网页聊天窗口 | 当前聊天窗口 session id |
| 一次微信咨询 | 当前会话 id |
| 一个工单 | ticket id |
| 一个 CRM 线索跟进 | lead conversation id |

当前版本会用 `accountId + dialogId` 隔离会话状态。同一个用户如果开启多个咨询窗口，只要 `dialogId` 不同，已收集资料和提问次数就不会串在一起。

## 5. profile 怎么传

`profile` 用来告诉 AI：这些资料已经知道了，不要重复问。

例如你的网站已经知道用户在深圳：

```json
{
  "accountId": "user-001",
  "dialogId": "dialog-001",
  "question": "你好",
  "profile": {
    "location": "深圳"
  }
}
```

如果用户已经登录并绑定手机号：

```json
{
  "accountId": "user-001",
  "dialogId": "dialog-001",
  "question": "想了解一下服务",
  "profile": {
    "phone": "13800138000"
  }
}
```

`profile` 的 key 要和模板里的字段 key 对应。

例如婚恋模板里：

```yaml
field_groups:
  core:
    - key: sex
    - key: age
    - key: education
    - key: occupation
    - key: location
```

那请求里就可以传：

```json
{
  "profile": {
    "sex": "男",
    "age": "30",
    "education": "本科",
    "occupation": "工程师",
    "location": "深圳"
  }
}
```

## 6. 响应格式

示例：

```json
{
  "success": true,
  "response": "你好呀，我在呢。你这边是男生还是女生呀？",
  "account_id": "user-001",
  "dialog_id": "dialog-001",
  "collected": {},
  "next_field": {
    "key": "sex",
    "label": "性别",
    "type": "enum",
    "required": true
  },
  "template_id": "matchmaking",
  "rag_sources": []
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `success` | 请求是否成功。 |
| `response` | AI 要回复给用户的话。 |
| `account_id` | 本次请求的用户 ID。 |
| `dialog_id` | 本次请求的会话 ID。 |
| `collected` | 本轮新增识别或接收到的模板字段，来源包括请求 `profile`、用户自然语言提取和待确认字段确认结果。 |
| `next_field` | 系统判断下一步最适合收集的字段。 |
| `template_id` | 当前使用的模板 ID。 |
| `rag_sources` | 如果启用 RAG，这里返回命中的知识来源。 |

## 7. 网页聊天接入示例

前端发送：

```js
await fetch("http://127.0.0.1:8000/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    accountId: localStorage.getItem("visitorId"),
    dialogId: sessionStorage.getItem("dialogId"),
    question: userInput,
    profile: {}
  })
});
```

后端返回 `response` 后，直接显示给用户。

## 8. 微信/企微 webhook 接入示例

伪代码：

```python
def handle_wechat_message(event):
    payload = {
        "accountId": event["openid"],
        "dialogId": event.get("conversation_id") or event["openid"],
        "question": event["text"],
        "profile": {}
    }
    result = post("http://127.0.0.1:8000/api/chat", json=payload)
    send_wechat_reply(event["openid"], result["response"])
```

## 9. CRM 接入示例

如果你已经有线索系统，可以把 CRM 里的 lead id 当作 `accountId`：

```json
{
  "accountId": "lead-10086",
  "dialogId": "lead-10086-chat-001",
  "question": "怎么收费？",
  "profile": {
    "location": "深圳",
    "phone": "13800138000"
  }
}
```

AI 会基于已有资料继续对话，减少重复提问。

## 10. 常见问题

### Q: 不传 dialogId 可以吗？

可以。当前 `dialogId` 是可选字段。

但如果你的系统里一个用户可能同时有多个咨询会话，建议传。

### Q: accountId 可以用手机号吗？

不建议。手机号属于敏感信息。

建议用你系统内部的用户 ID、openid、visitor id 或 lead id。

### Q: profile 里的字段随便写可以吗？

可以传任意对象，但只有模板里配置过的字段会被当作收集资料。

例如模板没有配置 `birthday`，即使传了也不会作为模板字段返回到 `collected`。

### Q: 修改模板后要重启吗？

当前模板加载有缓存。修改模板或 prompts 文件后，需要重启服务，或者在测试代码里调用 `reset_template_cache()`。

本地 CLI 重新运行 `t` 即可加载新配置。

### Q: 现在能从用户自然语言里自动提取字段吗？

可以。当前版本会基于模板配置做自然语言提取。

例如婚恋模板配置了 `sex/location/education`，用户说“男的，深圳，本科”，系统会尝试自动提取这些字段。教培模板配置了 `student_grade/subject`，用户说“孩子初二，想补数学”，系统会按教培字段提取。

默认情况下，模板里配置的资料字段和联系方式字段都会参与提取。低优字段即使不主动问，也可以被动提取；如果不想让某个字段被提取，可以在字段上配置 `extract: false`。

注意：自然语言提取需要配置大模型 Key。没有配置大模型时，仍然可以通过 `profile` 显式传入资料。

### Q: 如果我只想做智能客服，不想收集资料怎么办？

可以不配置字段：

```yaml
fields: []

field_groups:
  core: []
  medium: []
  low: []

contact:
  enabled: false
  methods: []
```

这样系统不会主动问资料，也不会提取资料，只会根据 `agent`、`faq`、`rag` 等配置回答用户问题。
