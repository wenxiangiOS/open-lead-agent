# 13 First Generation Delivery Rule

## 背景

当前对话链路里，用户可见话术在第一次 AI 生成之后，仍可能被以下环节再次改写：

- 收集落库后的 followup rewrite
- finalize 阶段的 core/contact regen
- 风格重写、bridge 重写

这会带来三个问题：

- 用户可见话术来源不唯一，调试困难
- 联系方式等场景出现第二次、第三次 AI 调用，耗时显著增加
- 第一次生成正确、后续改坏，导致合规和稳定性反复失控

## 统一规则

全项目统一采用以下硬规则：

1. 用户可见内容只来自第一次 AI 生成的话术。
2. 不允许第二次、第三次 AI 重新生成用户话术。
3. 后处理只允许做技术标签剥离，不允许改写文案。
4. 如果第一次 AI 失败，或者剥离后没有可展示话术，本轮直接静默。
5. 不向用户展示任何错误提示、系统异常、模板兜底。
6. 用户下一条消息到来时，再重新正常调用 AI 生成新话术。

## 适用范围

该规则覆盖整个项目，不分模块特例：

- 开场
- 核心字段收集
- 中等字段收集
- 核心字段解释型重问
- 中等字段再次追问
- 主字段加相近字段拼问
- 联系方式首次切入
- 电话追问
- 微信追问
- FAQ 打断后回主线
- 收尾阶段

## 链路定义

每轮对话只允许走以下链路：

1. 决策层产出结构化任务。
2. Prompt 层把该任务写成一次性可完成的生成指令。
3. 生成层只调用一次 AI，产出 `raw_first_generation`。
4. 交付层从 `raw_first_generation` 中提取 `display_text`。
5. `display_text` 非空则展示；为空则静默。

## 关键概念

### raw_first_generation

第一次 AI 返回的原始结果，可能同时包含：

- 用户正文
- `<extract>...</extract>`
- `<opening_intent>...</opening_intent>`

### display_text

最终给用户展示的正文。它必须直接来自 `raw_first_generation`，不能来自第二次 AI。

### 技术标签

技术标签是给系统内部消费的结构化块，不给用户展示。当前至少包括：

- `<extract>...</extract>`
- `<opening_intent>...</opening_intent>`

交付层只允许剥离这些技术标签，不允许改写正文语义。

## 允许的后处理

后处理只允许：

- 从原始结果中提取正文
- 剥离技术标签

后处理明确禁止：

- 风格重写
- bridge 重写
- 联系方式 regen
- 核心字段 regen
- 收集后根据新决策改写本轮文案
- 基于合规或自然度再调用 AI 改写一次

## 失败策略

如果出现以下任一情况：

- 第一次 AI 调用失败
- 第一次 AI 返回空
- 技术标签剥离后无正文

则本轮直接静默：

- 不展示错误
- 不展示模板兜底
- 不再次调用 AI
- 等用户下一条消息时重新正常处理

## 实施要求

### 必须删除的旧链路

在 `src/services/core/chat_service.py` 中删除：

- `refresh_turn_decision_after_collection` 里对 `_refresh_followup_after_collection(...)` 的调用
- `_refresh_followup_after_collection`
- `_rewrite_response_for_style`
- `_stabilize_style_response`
- `_rewrite_response_for_profile_bridge`
- `_enforce_profile_bridge_response`

在 `src/services/core/chat_service_finalize_service.py` 中删除：

- `_needs_core_soft_refusal_retry_regen`
- `_regenerate_core_soft_refusal_followup`
- `_looks_awkward_core_soft_refusal_retry`
- `_needs_contact_followup_regen`
- `_regenerate_contact_followup`

### 新增统一交付模块

新增统一交付模块，例如：

- `src/services/core/first_generation_delivery_service.py`

职责：

- 从第一次 AI 原始结果中提取正文
- 统一处理技术标签剥离
- 输出最终展示文本

该模块不得承担任何二次生成职责。

## 测试要求

测试要统一改成强约束：

1. 所有旧的 “应该 regen” 测试全部删除或改写。
2. 如果 finalize 或 refresh 阶段再次调用 AI，测试直接失败。
3. 重点覆盖：
   - 核心字段
   - 中等字段
   - 联系方式
   - FAQ 回主线
   - 技术标签剥离
   - 失败静默

## 最终原则

全项目最终只认四条：

1. 决策层决定问什么。
2. 第一次 AI 决定怎么说。
3. 交付层只剥离技术标签。
4. 失败就静默，等待用户下一条消息。
