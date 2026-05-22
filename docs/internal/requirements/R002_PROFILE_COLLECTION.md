# R002 资料收集需求

## 1. 文档定位

本文档定义资料字段如何配置、如何主动询问、如何被动收集，以及主字段和顺带字段的关系。

## 2. 需求

模板作者只需要配置“要收集哪些字段”，系统负责：

- 判断哪些字段还缺
- 选择下一轮最自然的问题
- 被动提取用户主动提供的信息
- 避免重复追问
- 在资料足够后交给联系方式流程

## 3. 背景

开源用户通常只知道自己要收集哪些资料，不应该要求他们配置复杂流程。

项目内部应该自动完成字段分层、字段路由、上下文追问和有效询问计数。

## 4. 字段分层

字段分为三层：

| 分组 | 作用 | 默认行为 |
| --- | --- | --- |
| `core` | 核心主线字段 | 默认主动问，默认有效询问 2 次 |
| `medium` | 中等字段 | 可以相近时顺带，默认有效询问 1 次 |
| `low` | 低优字段 | 不主动问，只被动收集 |

## 5. 主字段和顺带字段

每轮最多有：

- 一个主字段 `main_target`
- 一个可选顺带字段 `side_target`

规则：

- 主字段决定本轮主线。
- 顺带字段只能轻量出现，不能抢主线。
- 如果顺带字段不自然，宁可只问主字段。
- API 的 `next_field` 仍然代表主字段，避免破坏旧接入方。

## 6. 用户主动信息作为上下文锚点

如果用户主动提供信息，这个信息会成为上下文锚点。

例如：

```text
用户：我来自深圳
系统：收集 location=深圳
下一问：优先找和 location 相近的未收集核心字段，如 occupation
```

路由优先级：

1. 找相近的未收集核心字段。
2. 如果没有足够相近核心字段，再找强相关中等字段。
3. 如果都没有，就回到核心字段主线。

## 7. 配置

```yaml
field_groups:
  core:
    - key: location
      label: 所在城市
      ask: "你目前在哪个城市？"

    - key: occupation
      label: 职业
      ask: "你现在主要做什么工作？"

  medium:
    - key: monthly_income
      label: 月收入
      ask: "如果方便的话，也可以了解一下你的月收入区间。"

  low:
    - key: height
      label: 身高
      ask_limit: 0
```

## 8. 实现位置

- `src/templates/config.py`：字段配置模型和默认分层行为
- `src/collection/engine.py`：基础字段选择
- `src/collection/state.py`：字段状态
- `src/policy/field_routing.py`：上下文字段路由和 side target
- `src/understanding`：自然语言字段理解

## 9. 测试

- `tests/test_collection_engine.py`
- `tests/test_field_state.py`
- `tests/test_field_routing_policy.py`
- `tests/test_extraction_engine.py`

## 10. 当前状态

已实现基础版。

后续可增强：

- 字段亲近度可以进一步做成可配置权重。
- side_target 是否最终真的问出来，可以结合回复后质量检查进一步判断。
