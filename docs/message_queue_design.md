# 多次发送消息处理方案设计文档

> 创建时间：2026-03-06
> 状态：待实现
> 文档类型：设计稿，不代表当前线上/主链路已接入

## 一、背景

AI 最终要接入小红书 API，小红书用户有**快速连续发送多条短消息**的习惯，例如：

```
用户：你好
用户：我是看到帖子来的
用户：想了解一下那个女生
用户：她是哪里人呀
```

同时，AI 回复有时需要几十秒甚至 1-2 分钟，在此期间用户可能继续发送消息。

## 二、问题分析

### 问题 1：快速连续发送

当前实现中，`isProcessing = true` 时会阻止发送新消息，不符合小红书用户习惯。

### 问题 2：AI 思考期间收到新消息

```
0s    用户：想了解那个女生
30s   （AI 还在思考...）
35s   用户：她是哪里人呀  ← 补充信息
60s   AI 回复第一条... 但没有考虑用户的补充
```

### 问题 3：用户改变意图

```
0s    用户：想了解那个女生
40s   用户：算了，不想看了  ← 改变主意
60s   AI 回复：好的，让我给你介绍一下...  ← 已经不相关了
```

## 三、解决方案

### 核心设计：智能消息处理系统

#### 状态定义

| 状态 | 说明 | 用户发消息时的行为 |
|------|------|-------------------|
| **IDLE** | AI 空闲 | 启动短消息缓冲计时器 |
| **BUFFERING** | 等待用户说完 | 重置计时器，消息加入缓冲区 |
| **PROCESSING** | AI 正在处理 | 消息加入队列 |
| **QUEUED** | 有消息在排队 | 消息继续加入队列 |

#### 处理流程

```
用户发消息
    │
    ├── AI 空闲？ ─────────────────── 是 ──→ 进入 BUFFERING 状态
    │                                         启动 2.5 秒计时器
    │                                              │
    │                                         计时器到期
    │                                              │
    │                                              ↓
    │                                         合并缓冲区消息
    │                                         发送给 AI
    │                                         进入 PROCESSING 状态
    │
    └── AI 正在处理？ ──────────────── 是 ──→ 消息加入处理队列
                                               返回提示"已收到，稍后回复"
                                                    │
                                               AI 回复完成
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ↓                               ↓
                              队列有消息                        队列无消息
                                    │                               │
                                    ↓                               ↓
                              合并队列消息                      回到 IDLE 状态
                              发送给 AI
                              继续 PROCESSING
```

## 四、代码实现（参考）

### 后端核心类

```python
import asyncio
from collections import deque
from typing import Optional

class MessageState:
    IDLE = "idle"                    # 空闲
    BUFFERING = "buffering"          # 短消息缓冲中
    PROCESSING = "processing"        # AI 处理中
    QUEUED = "queued"                # 有排队消息

class UserSession:
    """每个用户的会话状态"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = MessageState.IDLE

        # 短消息缓冲（用于合并快速连续发送的消息）
        self.message_buffer: list = []
        self.buffer_timer: Optional[asyncio.Task] = None
        self.buffer_timeout = 2.5  # 秒

        # 处理队列（用于 AI 处理期间收到的消息）
        self.message_queue: deque = deque()

        # 当前处理任务
        self.current_task: Optional[asyncio.Task] = None

    def reset(self):
        """重置会话状态"""
        self.state = MessageState.IDLE
        self.message_buffer.clear()
        self.message_queue.clear()
        if self.buffer_timer:
            self.buffer_timer.cancel()
            self.buffer_timer = None


class MessageHandler:
    """消息处理器"""

    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.sessions: dict[str, UserSession] = {}
        self.buffer_timeout = 2.5

    def get_session(self, user_id: str) -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]

    async def handle_message(self, user_id: str, message: str) -> dict:
        """
        处理用户消息的主入口

        Returns:
            dict: {
                "status": "buffering" | "queued" | "processing" | "response",
                "message": "提示信息",
                "response": "AI回复（如果有）",
                "buffered_count": 缓冲消息数,
                "queued_count": 排队消息数
            }
        """
        session = self.get_session(user_id)

        if session.state == MessageState.IDLE:
            return await self._handle_idle(session, message)
        elif session.state == MessageState.BUFFERING:
            return await self._handle_buffering(session, message)
        elif session.state in [MessageState.PROCESSING, MessageState.QUEUED]:
            return await self._handle_processing_or_queued(session, message)

    async def _handle_idle(self, session: UserSession, message: str) -> dict:
        """AI 空闲时，启动缓冲"""
        session.message_buffer.append(message)
        session.state = MessageState.BUFFERING

        session.buffer_timer = asyncio.create_task(
            self._buffer_timeout(session)
        )

        return {
            "status": "buffering",
            "message": f"已收到消息，等待您说完...",
            "buffered_count": len(session.message_buffer)
        }

    async def _handle_buffering(self, session: UserSession, message: str) -> dict:
        """缓冲中，重置计时器"""
        session.message_buffer.append(message)

        if session.buffer_timer:
            session.buffer_timer.cancel()
        session.buffer_timer = asyncio.create_task(
            self._buffer_timeout(session)
        )

        return {
            "status": "buffering",
            "message": f"已收到 {len(session.message_buffer)} 条消息，等待您说完...",
            "buffered_count": len(session.message_buffer)
        }

    async def _handle_processing_or_queued(self, session: UserSession, message: str) -> dict:
        """AI 处理中，消息加入队列"""
        session.message_queue.append(message)
        session.state = MessageState.QUEUED

        return {
            "status": "queued",
            "message": f"已收到，AI 正在思考中，您的消息将在稍后处理...",
            "queued_count": len(session.message_queue)
        }

    async def _buffer_timeout(self, session: UserSession):
        """缓冲超时，合并消息并发送给 AI"""
        await asyncio.sleep(self.buffer_timeout)

        combined_message = "\n".join(session.message_buffer)
        session.message_buffer.clear()
        session.state = MessageState.PROCESSING

        try:
            response = await self.ai_service.chat(session.user_id, combined_message)

            if session.message_queue:
                queued_combined = "\n".join(session.message_queue)
                session.message_queue.clear()
                asyncio.create_task(
                    self._process_queued_messages(session, queued_combined, response)
                )
            else:
                session.state = MessageState.IDLE

            return response

        except Exception as e:
            session.state = MessageState.IDLE
            raise e

    async def _process_queued_messages(self, session: UserSession, message: str, previous_response: dict):
        """处理队列中的消息"""
        session.state = MessageState.PROCESSING

        try:
            response = await self.ai_service.chat(session.user_id, message)

            if session.message_queue:
                queued_combined = "\n".join(session.message_queue)
                session.message_queue.clear()
                await self._process_queued_messages(session, queued_combined, response)
            else:
                session.state = MessageState.IDLE

        except Exception as e:
            session.state = MessageState.IDLE
            raise e

    async def force_send(self, user_id: str) -> dict:
        """用户手动点击"说完了"，立即发送缓冲区消息"""
        session = self.get_session(user_id)

        if session.state != MessageState.BUFFERING:
            return {"status": "error", "message": "当前没有待发送的消息"}

        if session.buffer_timer:
            session.buffer_timer.cancel()
            session.buffer_timer = None

        return await self._buffer_timeout(session)
```

### API 接口设计

```python
# 小红书回调接口
@app.post("/api/xiaohongshu/message")
async def receive_message(request: Request):
    data = await request.json()
    user_id = data["user_id"]
    message = data["message"]

    result = await message_handler.handle_message(user_id, message)

    if result["status"] in ["buffering", "queued"]:
        return {"type": "hint", "message": result["message"]}
    else:
        return {"type": "response", "message": result["response"]}


@app.post("/api/xiaohongshu/force_send")
async def force_send(request: Request):
    """用户手动点击"说完了""""
    data = await request.json()
    user_id = data["user_id"]
    result = await message_handler.force_send(user_id)
    return result
```

## 五、方案优缺点

### 优点

| 优点 | 说明 |
|------|------|
| 符合用户习惯 | 小红书用户可以随意快速发送多条消息 |
| 消息不丢失 | 所有消息都会被处理 |
| 上下文完整 | 短时间内发的消息会合并，AI 能理解完整意图 |
| 体验流畅 | 用户不需要等待 AI 回复完才能发下一条 |
| 减少 API 调用 | 合并消息后一次调用，节省成本 |

### 缺点

| 缺点 | 说明 |
|------|------|
| 延迟感 | 2.5 秒缓冲让用户感觉"反应慢" |
| 回复分裂 | AI 处理队列时可能分两次回复 |
| 队列积压 | 如果 AI 很慢，队列可能越来越长 |
| 无法打断 | 用户改变主意后，旧消息仍会被处理 |
| 实现复杂 | 状态机 + 队列 + 异步处理 |

## 六、优化点

### 必须实现

| 优化点 | 说明 | 优先级 |
|--------|------|--------|
| 会话过期清理 | 避免内存泄漏 | 🔴 高 |
| 进度反馈 | 告诉用户当前状态 | 🔴 高 |
| AI 超时处理 | 超时后清空队列 | 🔴 高 |

### 建议实现

| 优化点 | 说明 | 优先级 |
|--------|------|--------|
| 智能判断"说完了" | 根据消息内容判断是否缓冲结束 | 🟡 中 |
| 消息优先级 | 联系方式等高优先级消息立即处理 | 🟡 中 |
| 队列上限 | 限制队列长度，防止积压 | 🟡 中 |
| 重复消息去重 | 避免发送重复内容 | 🟡 中 |
| 监控指标 | 收集关键指标用于优化 | 🟡 中 |

### 可选实现

| 优化点 | 说明 | 优先级 |
|--------|------|--------|
| 动态缓冲时间 | 根据消息长度调整等待时间 | 🟢 低 |
| 智能打断 | 检测"算了"等关键词，清空队列 | 🟢 低 |
| 相似消息合并 | 合并相似内容 | 🟢 低 |
| 预估等待时间 | 显示"预计等待 30 秒" | 🟢 低 |

## 七、监控指标

建议收集以下指标：

- `buffer_hit_count`: 缓冲命中次数
- `queue_hit_count`: 队列命中次数
- `avg_buffer_size`: 平均缓冲大小
- `avg_queue_size`: 平均队列大小
- `avg_wait_time`: 平均等待时间
- `avg_response_time`: AI 平均响应时间

## 八、相关文件

- 前端页面：`/test_page/static/mobile_final.html`
- 聊天服务：`/src/services/core/chat_service.py`
- API 路由：`/src/api/routes/chat.py`

## 九、实现计划

1. [ ] 创建 `MessageHandler` 类
2. [ ] 集成到现有 `core/chat_service.py`
3. [ ] 修改前端页面支持新状态显示
4. [ ] 添加监控埋点
5. [ ] 测试验证
6. [ ] 上线观察

---

*本文档待后续实现时更新*
