# Wrapper Risk Matrix

> 更新时间：2026-03-19
> 目标：给剩余兼容层 wrapper 做逐文件风险分级
> 原则：先分级，再清理；不靠感觉删文件

---

## 1. 分级规则

### `DELETE_CANDIDATE`

含义：

- 当前路径引用已清零或接近清零
- 不在包级导出主链中
- 删除后只需做小范围验证

### `MIGRATE_IMPORTS_FIRST`

含义：

- 文件本身是 wrapper
- 但运行时代码、测试或包导出仍在引用
- 只能先改 import，再考虑删文件

### `DO_NOT_TOUCH_NOW`

含义：

- 虽然某个路径是 wrapper，但它正处在核心桥接位置
- 或删除会牵动路由、worker、MQ、`ChatService`、`DialogueManager`
- 当前不建议继续动

---

## 2. 当前剩余 wrapper 总览

当前确认剩余 wrapper 共 20 个：

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection/domain/refusal_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/dialogue_manager.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/application/message_orchestrator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/queue_store.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/reply_delivery_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/message_queue_worker.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/reply_sender_worker.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/infrastructure/xhs_reply_client.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/interfaces/http/ingest_route.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/application/process_chat_turn.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_coordinator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_ending_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_rule_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/input_fallback_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/user_question_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`

说明：

- 之前已清掉 4 个低风险 wrapper
- 剩下这批整体风险显著更高

---

## 3. 风险分级

### 3.1 `DELETE_CANDIDATE`

当前没有建议直接继续删除的对象。

原因：

- 低风险、无引用、无包导出的 wrapper 已经在上一轮清掉
- 当前剩余项至少都挂着运行时、测试、包导出或核心桥接关系

结论：

- 现在不建议继续“直接删文件”

### 3.2 `MIGRATE_IMPORTS_FIRST`

这些文件后续可以清，但必须先迁引用。

#### 旧 services 侧 wrapper

- `/Users/eric/Desktop/doubao_mcp_server/src/services/application/process_chat_turn.py`
  - 当前引用：`src/services/core/chat_service.py`
  - 动作：先让 `ChatService` 直接 import `src.modules.conversation.application.process_chat_turn`

- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_coordinator.py`
  - 当前引用：`src/services/core/chat_service.py`
  - 动作：先让 `ChatService` 直接 import `src.modules.profile_collection.application.profile_collection_coordinator`

- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_rule_service.py`
  - 当前引用：`src/services/core/chat_service.py`
  - 动作：先让 `ChatService` 直接 import `src.modules.conversation.domain.conversation_rule_service`

- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/ask_tracking_service.py`
  - 当前引用：`tests/unit/test_ask_tracking_service.py`
  - 动作：先把测试改到模块路径

- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_policy.py`
  - 当前引用：
    - `src/services/core/dialogue_manager.py`
    - `tests/unit/test_profile_collection_policy.py`
  - 动作：先改 `DialogueManager` 和测试

- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_ending_service.py`
  - 当前引用：`tests/unit/test_conversation_ending_service.py`
  - 动作：先把测试改到模块路径

- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/input_fallback_service.py`
  - 当前引用：`tests/unit/test_nonsense_handler.py`
  - 动作：先把测试改到模块路径

- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/user_question_service.py`
  - 当前引用：`tests/unit/test_user_question_service.py`
  - 动作：先把测试改到模块路径

- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
  - 当前引用：
    - `src/services/__init__.py`
    - `src/services/core/dialogue_manager.py`
    - `src/services/data/__init__.py`
    - `tests/unit/test_extraction_service.py`
  - 动作：先改包导出、`DialogueManager`、测试

- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
  - 当前引用：
    - `src/services/__init__.py`
    - `src/services/data/__init__.py`
  - 动作：先改包导出

- `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`
  - 当前引用：`src/services/__init__.py`
  - 动作：先改包导出

### 3.3 `DO_NOT_TOUCH_NOW`

这些文件虽然是 wrapper，但现在仍处于核心桥接位置，当前不建议继续动。

#### 运行时桥接：modules -> old true source

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/dialogue_manager.py`
  - 被 `src/services/core/chat_service.py` 直接引用
  - 真正实现仍在 `src/services/core/dialogue_manager.py`

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection/domain/refusal_service.py`
  - 被 `src/services/core/chat_service.py` 直接引用
  - 真正实现仍在 `src/services/refusal_service.py`

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/application/message_orchestrator.py`
  - 被 `src/api/app.py`、`src/workers/message_queue_worker.py`、`src/api/routes/xiaohongshu_ingest.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/queue_store.py`
  - 被 `src/api/app.py`、`src/workers/message_queue_worker.py`、`src/workers/reply_sender_worker.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/reply_delivery_service.py`
  - 被 `src/workers/reply_sender_worker.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/message_queue_worker.py`
  - 被 `src/api/app.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/reply_sender_worker.py`
  - 被 `src/api/app.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/infrastructure/xhs_reply_client.py`
  - 被 `src/api/app.py` 直接引用

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/interfaces/http/ingest_route.py`
  - 被 `src/api/routes/__init__.py` 直接引用

原因：

- 这些 wrapper 不是“没人用的壳”，而是当前运行时的桥
- 要删它们，必须先完成更深一层真源迁移
- 这一步会碰到 `DialogueManager`、MQ、平台接入、worker

结论：

- 当前禁止继续动这一批

---

## 4. 推荐后续动作

### 路线 A：继续低速清理

只做 `MIGRATE_IMPORTS_FIRST` 这批里的“测试和包导出”替换：

1. 先改测试 import
2. 再改 `src/services/__init__.py`、`src/services/data/__init__.py`
3. 再改 `ChatService` 和 `DialogueManager` 的旧 wrapper import
4. 最后删对应旧壳

### 路线 B：立即停止

当前也完全合理，因为：

- 高风险 wrapper 已经筛出来了
- 继续删的收益开始明显下降
- 后续很容易碰到真实业务真源

### 已验证的风险

2026-03-19 已实际尝试过一轮“只改测试和包导出 import”的轻量迁移，结果触发：

- `src/services/__init__.py`
- `src/services/core/chat_service.py`
- `src/modules/profile_collection/domain/ask_tracking_service.py`

之间的循环导入链。

结论：

- 当前剩余 wrapper 不能再按“轻量 import 迁移”继续推进
- 后续若继续，必须先专项处理 package 初始化与循环依赖

---

## 5. 一句话结论

当前仓库里剩余 wrapper 已经不适合继续“直接删除”；  
后续如果还要清理，只能先迁 import，再删旧壳，而且优先动测试和包导出，不要先碰 MQ、平台接入和 `DialogueManager` 桥接层。
