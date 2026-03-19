# Repo Cleanup Inventory

> 更新时间：2026-03-19
> 目标：给当前仓库提供一份可执行的清理清单
> 范围：废弃代码、冗余代码、空目录、生成产物、历史资料

---

## 1. 结论

当前仓库的主要清理对象不是空目录，而是以下四类：

- 生成产物和缓存目录
- 未接入主链路的完整子系统
- 兼容层 wrapper / 双路径共存
- 历史测试、历史示例、历史文档

当前实际扫描结果：

- 业务空目录：未发现
- 唯一空目录：`.git/refs/tags`
- 兼容壳文件：至少 24 个
- `reports/real_ai` 文件数：110
- `reports/real_ai_realism` 文件数：8
- `reports/mq` 文件数：7

---

## 2. 可立即删除

这类内容不属于主业务代码，可以直接清理，不影响运行逻辑。

### 2.1 缓存和编译产物

- `/Users/eric/Desktop/doubao_mcp_server/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/src/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/examples/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/scripts/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/test_page/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/tests/__pycache__/`
- `/Users/eric/Desktop/doubao_mcp_server/.pytest_cache/`
- `/Users/eric/Desktop/doubao_mcp_server/tests/.pytest_cache/`

说明：

- 这些目录都是运行缓存或测试缓存
- 删除后可自动重新生成

### 2.2 非必要历史报告

- `/Users/eric/Desktop/doubao_mcp_server/reports/real_ai/`
- `/Users/eric/Desktop/doubao_mcp_server/reports/real_ai_realism/`

建议动作：

- 保留 `latest.json` 和 `latest.md`
- 删除带时间戳的历史回归文件

原因：

- 当前 `reports/real_ai/` 有 110 个文件，明显属于累积产物
- 当前 `reports/real_ai_realism/` 有 8 个文件，结构也属于同类历史产物

注意：

- `/Users/eric/Desktop/doubao_mcp_server/reports/mq/` 不建议直接删，因为它被 MQ 设计和验收文档反复引用

---

## 3. 建议归档

这类内容不是垃圾代码，但当前不属于主链路，继续放在主目录里会增加噪音。

### 3.1 未接入子系统

- `/Users/eric/Desktop/doubao_mcp_server/src/database/`
- `/Users/eric/Desktop/doubao_mcp_server/src/monitoring/`
- `/Users/eric/Desktop/doubao_mcp_server/src/plugins/`
- `/Users/eric/Desktop/doubao_mcp_server/plugins/`

判断依据：

- 当前扫描没有发现主链路对 `src.database` 或 `src.plugins` 的实际 import
- 仓库已有文档明确把这些列为“未接入子系统”：
  - `/Users/eric/Desktop/doubao_mcp_server/docs/unused_subsystems_review.md`
  - `/Users/eric/Desktop/doubao_mcp_server/docs/archive_strategy.md`

建议动作：

- 不直接删除
- 迁移到归档目录或单独子仓
- 在 README 或 docs 中保留指向说明

当前状态：

- 已于 2026-03-19 迁移到 `/Users/eric/Desktop/doubao_mcp_server/archive/`

### 3.2 历史测试和归档示例

- `/Users/eric/Desktop/doubao_mcp_server/tests/_deprecated/`
- `/Users/eric/Desktop/doubao_mcp_server/examples/archive/`
- `/Users/eric/Desktop/doubao_mcp_server/docs/archive/`

说明：

- 这些目录本身已经带有历史语义
- 适合保留，但不应继续作为当前实现参考

当前状态：

- `/Users/eric/Desktop/doubao_mcp_server/tests/_deprecated/` 已于 2026-03-19 迁移到 `/Users/eric/Desktop/doubao_mcp_server/archive/tests/_deprecated/`

---

## 4. 暂时保留

这类内容虽然冗余，但当前还不能直接删。

### 4.1 兼容层 wrapper

以下文件是当前识别到的轻量转发壳，删除风险高于收益：

- `/Users/eric/Desktop/doubao_mcp_server/src/models/chat_flow.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection/domain/refusal_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/dialogue_manager.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/application/message_orchestrator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/domain/intent_classifier.py`
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
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/expectation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/greeting_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/input_fallback_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/user_question_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`

原因：

- 当前仍存在双路径 import
- 部分运行时入口仍依赖旧路径
- `message_queue`、`platform_xiaohongshu`、`dialogue_manager` 还没完成真源迁移

### 4.2 仍在主链路中但结构偏重的核心文件

- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/dialogue_manager.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/message_orchestrator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/queue_store.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/contact_collection_service.py`

说明：

- 这些文件不是废弃代码
- 但仍是当前仓库里比较重的“真实业务真源”
- 只能在专项迁移和回归验证后处理

### 4.3 测试页面

- `/Users/eric/Desktop/doubao_mcp_server/test_page/`

说明：

- 它不是主业务代码
- 但 [main.py](/Users/eric/Desktop/doubao_mcp_server/main.py) 仍有挂载逻辑
- 当前不能视为纯垃圾目录

---

## 5. 当前不建议删除

以下内容当前不建议直接删：

- `/Users/eric/Desktop/doubao_mcp_server/src/services/`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/`
- `/Users/eric/Desktop/doubao_mcp_server/src/workers/`
- `/Users/eric/Desktop/doubao_mcp_server/reports/mq/`
- `/Users/eric/Desktop/doubao_mcp_server/test_page/`

原因：

- 仍存在 live runtime import
- 文档、脚本、测试仍有引用
- 当前清理收益低于回归风险

---

## 6. 推荐清理顺序

### 第一批：低风险

1. 删除 `__pycache__` 和 `.pytest_cache`
2. 压缩或删除 `reports/real_ai/` 的历史时间戳文件
3. 压缩或删除 `reports/real_ai_realism/` 的历史时间戳文件

### 第二批：中风险

1. 将 `src/database/` 归档
2. 将 `src/monitoring/` 归档
3. 将 `src/plugins/` 和 `plugins/` 归档
4. 将 `tests/_deprecated/` 移出主测试视野

### 第三批：高风险

1. 继续做兼容层真源迁移
2. 清理双路径 import
3. 最后再删除 wrapper 文件

---

## 7. 一句话判断

当前仓库最大的问题不是“空文件夹太多”，而是：

- 兼容层壳文件偏多
- 未接入子系统仍在主目录
- 历史报告和缓存产物堆积较多

如果要清理，最先动缓存和历史报告；最晚动兼容层和核心业务真源。

---

## 8. 当前停止点

截至 2026-03-19，低风险和中风险两批清理已经完成：

- 已清理缓存目录和历史 `real_ai` 报告
- 已将未接入子系统和历史测试迁入 `/archive`
- 已删除少量低风险 wrapper

同时也已验证出一个新的约束：

- 继续做“测试 import / 包导出 import 迁移”会触发 `src/services/__init__.py` 相关循环依赖
- 这说明剩余 wrapper 清理已经不再是轻量任务

因此当前建议：

- 停止继续做 wrapper 轻量清理
- 如果后续一定要继续，先做 `services package` 解耦与循环依赖专项分析
