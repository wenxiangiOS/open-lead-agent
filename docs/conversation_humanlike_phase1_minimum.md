# Conversation Humanlike Phase 1 Minimum

- 更新时间: 2026-03-25
- 文档定位: 第一阶段最小闭环实施清单
- 目标: 不一次做完全部拟人化优化，先用最小改动解决最明显的问题

## 项目级约束

1. 本阶段不把 token / 调用成本作为决策依据
2. 不要为了省成本去削弱生成质量
3. 短答允许继续走重模型
4. 当前 Phase 1 的核心目标是:
   - 减少重复追问
   - 降低元策略话术
   - 提升 complaint repair 能力

## Phase 1 只做 3 件事

1. `complaint / repair` 意图
2. 偏好类去重 guard
3. 去掉高频元策略外显话术

这三项优先级最高，因为它们直接决定:

- 用户会不会觉得“你问了一遍又一遍”
- 对话会不会像“系统在执行策略”
- 用户抱怨后系统会不会修复

## Phase 1 要解决的现象

### 1. 用户抱怨问太多时，系统没有真正修复

错误表现:

- 用户: `这个是不是问的次数太多了？`
- AI: `我先不连着追问了，你继续说`

问题:

- 没明确承认刚才重复了
- 还在解释策略
- 下一轮大概率继续问

目标:

- 把这类输入识别成 complaint
- 进入 repair 模式
- 当前轮不追字段

### 2. 用户已经给过偏好，系统还在重问

错误表现:

- 用户: `同城吧`
- AI: `你最看重哪一点，我按这个优先筛`

问题:

- 已有偏好后仍然发泛化偏好问题

目标:

- 有偏好就切主线，不再重问偏好总类

### 3. 系统频繁暴露内部控制话术

错误表现:

- `那我们就按90后来聊`
- `我们先不连着问资料`
- `这轮我先不把资料问得太密`

问题:

- 这些是内部调度语言，不像真人聊天

目标:

- 直接压掉或显著降频
- 只保留自然确认

## Phase 1 范围外

第一阶段先不要做:

1. 短答单独轻量生成分支
2. FAQ 后 bridge-back
3. 低频 profile summary
4. 字段优先级大调整
5. `partner_requirement` 深度子槽拆分

说明:

- Phase 1 明确不处理“为了省成本而拆分短答路由”的问题
- 当前实现已统一回主模型路径，后续也不建议恢复轻量生成分支

这些都属于 Phase 2 及以后。

## Phase 1 详细执行要求

### A. complaint / repair

#### 触发样式

- `是不是问太多了`
- `怎么一直问`
- `问了一遍又一遍`
- `你怎么老问这个`
- `别一直问资料`
- `有点烦`

#### 决策要求

- `intent = complaint`
- `primary_move = repair_and_release`
- `allow_contact_target = False`
- `allow_medium_target = False`
- 当前轮不主动问字段

#### 回复要求

必须包含:

1. 承认刚才问得有点密
2. 当前轮降压
3. 给用户开放表达空间

推荐骨架:

- `是，我刚才这边问得有点密了。`
- `这轮我先不继续追资料。`
- `你想先说你的要求，或者你最在意哪类人，我顺着你说。`

#### cooldown 要求

- complaint 命中后至少 1 轮 cooldown
- cooldown 期间不主动追字段

### B. 偏好类去重 guard

#### 最低要求

如果 `partner_requirement` 已非空，则禁止再发:

- `你最看重哪一点`
- `你更在意哪几点`
- `你可以先说一个最在意的匹配点`

#### 允许的行为

- 确认已有偏好
- 切到真正缺失字段

示例:

- 用户: `同城吧`
- AI: `好，你比较看重同城。你这边现在主要做什么工作？`

### C. 元策略话术清洗

#### 默认压掉或降频的表达

- `按X来聊`
- `按这个方向来聊`
- `先不连着问资料`
- `这轮先不把资料问得太密`
- `按这个优先推进`
- `按这个优先筛`

#### 替换原则

- 不解释系统策略
- 用短确认替代

示例:

原句:

- `好，那我们就按90后来聊。`

改成:

- `90后是吧。`
- `那年龄段我大概有数了。`

## 推荐修改文件

### 1. `src/services/core/chat_service.py`

建议新增或扩展:

- `detect_complaint_or_conversation_fatigue(...)`
- `build_repair_response(...)`
- `should_block_generic_preference_prompt(...)`
- `sanitize_strategy_leakage_phrases(...)`

### 2. `src/services/core/dialogue_manager.py`

需要改:

- 选择下一问时检查 `partner_requirement`
- 命中后不再发泛化偏好句

### 3. `src/modules/conversation/domain/turn_decision.py`

需要支持:

- `intent = complaint`
- `primary_move = repair_and_release`

### 4. `src/modules/conversation/application/process_chat_turn.py`

需要支持:

- complaint 轮状态流转
- complaint cooldown 写入 / 读取

## Phase 1 测试要求

### 单元测试

至少覆盖:

1. 用户说“是不是问太多了”时命中 complaint
2. complaint 回复当前轮不再追字段
3. 已有 `partner_requirement` 后，不再问“最看重哪一点”
4. 元策略话术被清洗

### 回归脚本

最少覆盖这个多轮对话:

- `你好 -> 男的 -> 90后 -> 深圳 -> 同城吧 -> 对方不要超过30岁 -> 这个是不是问的次数太多了`

验收:

- 不再重问偏好
- 用户抱怨后进入 repair
- “按X来聊 / 不连着问资料”显著下降

## Phase 1 完成标准

满足以下条件即可算第一阶段完成:

1. 用户抱怨“问太多”时，系统不再继续字段追问
2. 已有偏好后，不再重问泛化偏好句
3. 长对话里“按X来聊 / 不连着问资料”显著下降

## 和总规格的关系

本文件是最小落地版。

完整方案见:

- `docs/conversation_humanlike_execution_spec.md`

如果资源有限，先做本文件内容；如果时间充足，再继续做完整规格中的 Phase 2 项。
