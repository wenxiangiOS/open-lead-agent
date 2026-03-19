# Project Status Summary

> 更新时间：2026-03-18
> 目标：给当前仓库提供一份简洁、可交接的状态总结
> 适用对象：当前维护者、后续接手的模型或工程师

---

## 1. 结论

当前项目已经完成本轮主要的结构重构目标，适合先进入稳定阶段。

准确说法是：

- 功能主链路是可用的
- 三档重构方案已经完成
- 兼容层清理已经启动，并完成了两批低风险真源迁移
- 但兼容层清理还没有彻底收尾
- 当前不建议继续做大规模结构改造

---

## 2. 已完成

### 2.1 架构重构已完成

以下文档定义的三档方案已经完成：

- `/Users/eric/Desktop/doubao_mcp_server/docs/refactor_execution_plans.md`

当前阶段结论：

- landed plan completed
- recommended plan completed
- best plan completed through `C4`

关键落地结果：

- `ChatService.process_chat_request` 已退为兼容入口
- 主聊天编排已通过 `ProcessChatTurnUseCase`
- 规则早返回已抽成显式规则链
- 联系方式状态已显式表达
- 同步聊天、异步 queue、小红书 ingest 已统一到 command/result 协议

### 2.2 模块化目录已接通

以下模块目录已建立并参与运行时：

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/shared`

### 2.3 第一批兼容层真源迁移已完成

`profile_collection` 真源已经迁入模块路径：

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/field_skip_service.py`

旧路径现已退为兼容 wrapper：

- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`

### 2.4 第二批兼容层真源迁移已完成

`conversation` 用户侧服务真源已经迁入模块路径：

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/greeting_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/conversation_ending_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/expectation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/input_fallback_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/user_question_service.py`

旧路径现已退为兼容 wrapper：

- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/greeting_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_ending_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/expectation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/input_fallback_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/user_question_service.py`

---

## 3. 已验证

本轮已经做过多轮聚焦回归，当前可确认：

- `93 passed, 1 skipped`
- `29 passed`
- `73 passed`

覆盖范围包括：

- chat route protocol path
- contact collection
- profile collection
- message orchestrator
- message queue worker
- reply sender worker
- message queue integration pipeline

说明：

- 本地 HTTP 小红书投递 e2e 在某些环境下可能被跳过
- 当前没有迹象表明本轮结构重构引入了明显回退

---

## 4. 还没有完成

### 4.1 兼容层没有彻底清理完

当前仍然存在大量兼容 wrapper 和双路径共存。

例如：

- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py` 仍是 live runtime entry
- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/dialogue_manager.py` 还没有完成真源迁移
- `message_queue` 大部分模块路径还只是外层壳或尚未做真源迁移
- `platform_xiaohongshu` 仍未做完整真源迁移
- `contact_collection` 业务真源仍保留在旧路径

### 4.2 旧路径还不能大规模删除

虽然很多旧路径已退成 wrapper，但还没有进入“可一口气删掉”的状态。

原因：

- 仍有运行时引用
- 仍有测试直接引用旧路径
- 仍有部分模块文件反向依赖旧实现

### 4.3 这不是“完全收尾”状态

当前状态更准确地说是：

- 架构重构达到稳定里程碑
- 兼容层清理进入中段
- 不是仓库终局状态

---

## 5. 为什么现在建议暂停

当前最重要的不是继续拆，而是控制风险。

暂停的原因：

1. 当前已经拿到了主要收益
- 主链路收口了
- 模块化结构已经建立
- 协议统一已经完成

2. 后续继续拆的收益下降
- 剩下 mostly 是兼容层、真源迁移、删 wrapper
- 这些工作收益更偏“整洁”，不是核心能力提升

3. 后续继续拆的风险上升
- 容易碰到 `dialogue_manager`
- 容易碰到 `message_queue`
- 容易误伤联系方式业务真源

4. 当前更适合进入稳定验证期
- 补端到端验证
- 观察行为是否一致
- 清理真实回归问题

---

## 6. 现在建议做什么

建议优先级如下：

1. 先停止大规模结构改造
2. 保留当前状态作为稳定里程碑
3. 继续做更广的回归验证或真实业务验证
4. 如果后面还要继续，只按兼容层计划小步推进

相关文档：

- `/Users/eric/Desktop/doubao_mcp_server/docs/refactor_execution_plans.md`
- `/Users/eric/Desktop/doubao_mcp_server/docs/compat_cleanup_plan.md`

---

## 7. 如果后面一定要继续

只建议两种继续方式。

### 7.1 保守继续

只做兼容层清理，不改业务逻辑。

优先考虑：

- 清理 runtime import 指向
- 逐步减少旧路径 wrapper 依赖
- 最后再考虑删除 wrapper

### 7.2 验证优先

不再做结构改造，改做：

- 更完整回归测试
- e2e 验证
- 人工对话行为对比
- MQ 异步链路验证

---

## 8. 当前不建议做什么

1. 不建议继续大搬目录
2. 不建议直接删一批旧文件
3. 不建议现在动 `contact_collection` 业务真源
4. 不建议现在动 `message_queue` 真源迁移
5. 不建议把这轮重构和策略优化混在一起

---

## 9. 交接一句话版本

如果后续要交给其他模型，最短可以这么描述：

```text
当前项目的三档结构重构方案已完成，模块化主路径已打通，profile_collection 和 conversation 两批低风险真源迁移已完成；当前应视为稳定里程碑，优先做回归验证和谨慎的兼容层清理，不建议继续做大规模结构改造。
```
