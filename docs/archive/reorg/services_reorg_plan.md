> 归档说明：本文件已归档，反映的是早期 `src/services/` 重组设想，不代表当前最新现状。
> 当前项目状态请优先参考：`docs/project_status_summary.md`、`docs/refactor_execution_plans.md`、`docs/compat_cleanup_plan.md`

# Services 重组方案

更新时间：2026-03-14

## 目标

当前 `src/services/` 已经不算失控，但文件类型开始混在一起：

- 有主编排层
- 有资料收集策略层
- 有对话表现层
- 有提取/校验/存储层
- 还有 prompt 中心

继续全部平铺在一个目录下，后续维护成本会越来越高。

本方案的目标不是立即迁移，而是先定义未来的目标结构和迁移顺序。

---

## 目标目录结构

```text
src/services/
  core/
    chat_service.py
    dialogue_manager.py

  collection/
    profile_collection_policy.py
    contact_collection_service.py
    ask_tracking_service.py
    field_skip_service.py
    refusal_service.py

  conversation/
    conversation_ending_service.py
    greeting_service.py
    input_fallback_service.py
    expectation_service.py

  data/
    extraction_service.py
    validation_service.py
    user_service.py
    redis_service.py

  prompts/
    prompts.py
```

---

## 分组原则

### core/

放主流程骨架。

- `chat_service.py`
  - 主编排层
  - 决定调用顺序

- `dialogue_manager.py`
  - 对话上下文
  - prompt 组装

### collection/

放资料收集与联系方式收集相关的策略和状态管理。

- `profile_collection_policy.py`
- `contact_collection_service.py`
- `ask_tracking_service.py`
- `field_skip_service.py`
- `refusal_service.py`

### conversation/

放对话表现层和会话体验层逻辑。

- `conversation_ending_service.py`
- `greeting_service.py`
- `input_fallback_service.py`
- `expectation_service.py`

### data/

放提取、校验、存储。

- `extraction_service.py`
- `validation_service.py`
- `data/user_service.py`
- `data/redis_service.py`

### prompts/

单独放 prompt 中心。

- `prompts.py`

这样可以避免把“提示词规则文件”继续和真正的 service 平铺混放。

---

## 现有文件映射表

| 当前文件 | 目标位置 |
|---|---|
| `src/services/chat_service.py` | `src/services/core/chat_service.py` |
| `src/services/dialogue_manager.py` | `src/services/core/dialogue_manager.py` |
| `src/services/profile_collection_policy.py` | `src/services/collection/profile_collection_policy.py` |
| `src/services/contact_collection_service.py` | `src/services/collection/contact_collection_service.py` |
| `src/services/ask_tracking_service.py` | `src/services/collection/ask_tracking_service.py` |
| `src/services/field_skip_service.py` | `src/services/collection/field_skip_service.py` |
| `src/services/refusal_service.py` | `src/services/collection/refusal_service.py` |
| `src/services/conversation_ending_service.py` | `src/services/conversation/conversation_ending_service.py` |
| `src/services/greeting_service.py` | `src/services/conversation/greeting_service.py` |
| `src/services/input_fallback_service.py` | `src/services/conversation/input_fallback_service.py` |
| `src/services/expectation_service.py` | `src/services/conversation/expectation_service.py` |
| `src/services/extraction_service.py` | `src/services/data/extraction_service.py` |
| `src/services/validation_service.py` | `src/services/data/validation_service.py` |
| `src/services/user_service.py` | `src/services/data/user_service.py` |
| `src/services/redis_service.py` | `src/services/data/redis_service.py` |
| `src/services/prompts.py` | `src/services/prompts/prompts.py` |

---

## 推荐迁移顺序

### 第一批：低风险文件

优先迁移新拆出的轻模块和 prompt：

- `greeting_service.py`
- `expectation_service.py`
- `input_fallback_service.py`
- `ask_tracking_service.py`
- `prompts.py`

当前状态：

- 已完成

原因：

- import 影响面相对小
- 业务耦合比主链路低
- 容易验证

### 第二批：中风险文件

- `profile_collection_policy.py`
- `contact_collection_service.py`
- `conversation_ending_service.py`

当前状态：

- 已完成

原因：

- 这些文件已经是核心业务模块
- 但仍然比 `chat_service.py` 更容易独立迁移

### 第三批：高风险文件

- `dialogue_manager.py`
- `extraction_service.py`
- `validation_service.py`
- `user_service.py`
- `redis_service.py`
- `chat_service.py`

当前状态：

- `dialogue_manager.py` 已完成
- `extraction_service.py` 已完成
- `validation_service.py` 已完成
- `user_service.py` 已完成
- `redis_service.py` 已完成
- 其余待迁移

原因：

- 导入链广
- 主流程依赖重
- 迁移后需要更完整的回归验证

---

## 为什么现在不建议一次性全迁

1. 一次性全改 import，容易把仓库重新搞乱
2. 当前主链路正在持续调整，边改逻辑边改目录风险太高
3. 目录迁移属于结构性改动，适合单独作为一个 task 做
4. 先把目标结构写清楚，再分批迁移，更容易 review 和回退

---

## 实施建议

如果后续真正执行目录迁移，建议每次只做一批，并遵循：

1. 只做目录迁移，不混入业务逻辑改动
2. 迁移后立即修 import
3. 迁移后立即跑最小可行回归
4. 同步更新结构文档

---

## 当前结论

`src/services/` 现在已经值得做二级目录分组，但不建议立刻一口气全迁。

正确策略是：

- 先定结构
- 再分批迁移
- 每批迁移都单独验证
