# P0 时延优化执行记录（2026-03-18）

## 本轮目标
在不改变对话逻辑与规则语义前提下，先落地工程层提速（P0）。

## 已完成改动

1. 队列参数默认值下调（更偏实时）：
   - `MQ_DEBOUNCE_MS`: 300
   - `MQ_DEBOUNCE_APPEND_MS`: 200
   - `MQ_DEBOUNCE_MAX_MS`: 1200
   - 文件：`src/services/queue/queue_store.py`

2. 队列参数支持 `.env` 覆盖：
   - `queue_store._cfg()` 增加 env fallback 与类型解析
   - 文件：`src/services/queue/queue_store.py`

3. worker / sender 轮询默认值下调：
   - `mq_worker_poll_ms`: 20
   - `mq_sender_poll_ms`: 100
   - 文件：`src/api/app.py`

4. 在线 AI 快失败策略：
   - `AI_CHAT_MAX_RETRIES` 默认 1
   - `AI_CHAT_RETRY_DELAY_SECONDS` 默认 0.5
   - `CHAT_AI_TIMEOUT_SECONDS` 默认 45
   - 文件：`src/services/ai_service.py`、`src/services/core/chat_service.py`

5. 测试页回执轮询：
   - `pollReplies` 间隔 1000ms -> 250ms
   - 文件：`test_page/static/mobile_final.html`

6. `.env.example` 已同步新增/更新上述参数。

7. FAQ 快速直出（P1 首项）：
   - 命中标准 FAQ 问法时，直接返回业务模板答案，不走大模型生成。
   - 未命中时保持原有 AI 流程不变。
   - 文件：`src/services/conversation/user_question_service.py`、`src/services/core/chat_service.py`

8. 答疑优先轻量提示词（P1 第二项）：
   - 命中“答疑优先”但未命中 FAQ 快速模板时，改用轻量答疑提示词，减少 token 负担。
   - 文件：`src/services/prompts/prompts.py`、`src/services/prompts/__init__.py`、`src/services/core/dialogue_manager.py`

9. 模型路由（P2 进阶，安全回退）：
   - 新增“上下文长度 + 意图复杂度 + 风险等级”路由，低风险低复杂度轮次可用快模型，高风险轮次强制主模型。
   - 若未配置 `AI_FAST_MODEL_NAME` 或关闭 `AI_ROUTING_ENABLED`，自动回退主模型。
   - 文件：`src/services/core/chat_service.py`、`src/services/ai_service.py`、`.env.example`

## 本轮验证

1. 编译检查：
   - `python3 -m compileall src/services/queue/queue_store.py src/services/ai_service.py src/services/core/chat_service.py src/api/app.py`
   - 结果：通过

2. 单元测试：
   - `pytest -q -o addopts='' tests/unit/test_user_question_service.py tests/unit/test_chat_service_regressions.py tests/unit/test_contact_collection_service.py tests/unit/test_queue_store.py tests/unit/test_message_orchestrator.py tests/unit/test_message_queue_worker.py tests/unit/test_reply_sender_worker.py tests/unit/test_chat_route_debug.py`
   - 结果：88 passed

3. FAQ 快速通道场景验证（重点）：
   - `python3 scripts/run_real_ai_regression.py --scenario-id faq_priority_mediator --scenario-id faq_priority_fee --scenario-id faq_priority_how_match --scenario-id faq_priority_success_rate --verbose`
   - 结果：4/4 通过，命中 FAQ 快速通道的第2轮响应耗时约 `0.22~0.23s`。

4. smoke 回归（全局）：
   - `python3 scripts/run_real_ai_regression.py --profile smoke`
   - 结果：当前执行环境 AI 外网连接错误（Connection error），本次 smoke 不可作为真实性能结论。

## 待完成

1. 在可用 AI 网络环境下执行：
   - `python3 scripts/run_real_ai_regression.py --verbose`
2. 产出前后时延对比报告（P50/P95/P99、平均、最长）。
