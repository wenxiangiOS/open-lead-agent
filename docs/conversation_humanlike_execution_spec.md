# Conversation Humanlike Execution Spec

- 更新时间: 2026-03-25
- 目标读者: 后续接手实现该优化的模型 / 工程师
- 文档定位: 直接执行用，不是讨论稿

## 快速入口

如果只打算先做最小闭环，优先看:

- `docs/conversation_humanlike_phase1_minimum.md`

## 项目级约束

1. 本项目当前阶段不把 token / 调用成本作为优化约束
2. 优化优先级按以下顺序理解:
   - 拟人化
   - 对话自然度
   - 重复追问控制
   - 动作一致性
   - 时延体验
   - 门禁表现
3. 不要因为“省成本”而削弱生成质量
4. 短答允许继续走重模型；如果后续要引入轻量路径，其目标也只能是改善时延与自然度，不能以省成本为理由替代主生成能力

## 背景

当前对话系统已经去掉了 `fixed_template` 主链路，但真实对话里仍然暴露出以下核心问题:

1. 用户已经给过偏好后，系统还会同义重问，例如已经有 `同城`、`年龄不超过30`，还继续问“你最看重哪一点”
2. 回复里高频出现元策略话术，例如“那我们就按90后来聊”“我们先不连着问资料”“我按这个优先推进”
3. FAQ / 边界轮结束后，回主线很生硬，没有自然桥接
4. 用户抱怨“问了一遍又一遍”“是不是问太多了”时，没有进入真正的 repair 模式
5. 短答输入如 `男的 / 90后 / 深圳 / 本科 / 4万左右` 全走重模型，时延偏高，且在当前 prompt 约束下仍然容易输出重复骨架
6. 对话像“会采字段的策略机”，不像“会承接的真人”

本次优化的目标不是简单润色文案，而是系统性改造:

- 降低重复追问
- 降低元策略泄漏
- 提升承接和修复能力
- 改善短答场景时延与自然承接
- 保持现有业务边界、风险控制、联系方式约束不被破坏

## 强约束

1. 不要重新引入 `fixed_template` 主链路
2. 不要只改文案，必须改决策逻辑
3. 优先修 complaint / 去重 / bridge，再做风格优化
4. 修改后必须补单测和多轮回归
5. 不允许为了降低时延而退回到硬编码回复状态机

## 设计原则

1. 先承接，再推进
2. 不重复问同一语义槽
3. 不向用户暴露内部策略
4. FAQ / 边界 / 投诉都必须能自然回主线
5. 轻输入走轻路径，重输入走重路径
6. 用户一旦表达不适，要优先修复体验

## 需要解决的具体现象

### 1. 偏好类重复追问

错误示例:

- 用户: `同城吧`
- AI: `你最看重哪一点，我按这个优先筛`

错误原因:

- `partner_requirement` 已经有值
- 系统仍然生成泛化偏好问题

目标行为:

- 用户给了 `同城`
- AI 确认一次后切回真正缺失字段，例如工作、婚姻、学历

### 2. 元策略话术泄漏

高频压制的句式:

- `那我们就按X来聊`
- `我先按这个方向来聊`
- `我们先不连着问资料`
- `这轮我先不把资料问得太密`
- `我按这个优先推进`
- `我按这个优先筛`

这些内容属于内部调度语言，不应该高频暴露给用户。

### 3. FAQ 后主线桥接缺失

错误示例:

- 用户问: `可以看对方照片吗？`
- AI 回答隐私边界
- 下一轮直接跳回: `你现在在哪个城市？`

目标行为:

- FAQ 收束一句
- 再自然接主线

示例:

- `这块先不往下走。你现在主要在哪个城市？`

### 4. complaint 轮不会修复

错误示例:

- 用户: `这个是不是问的次数太多了？`
- AI: `我先不连着追问了，你继续说`

这不算真正 repair，因为:

- 没有承认重复
- 没有交还主导权
- 下一轮很可能继续问

目标行为:

- 明确承认问得有点密
- 本轮不追字段
- 给用户一个可继续说的开放方向

### 5. 短答输入全走重模型

错误示例:

- 用户: `男的`
- 仍然走 `prompt_chars ≈ 5900`
- `input_tokens ≈ 4000+`
- `ai_call ≈ 7-12s`

目标行为:

- 短答场景走轻量生成层
- 仍然由模型生成，但上下文极简
- 不回退到固定模板

## 总体方案

### A. 新增 complaint / repair 意图

#### 目标

当用户抱怨“问太多 / 太重复 / 别一直问”时，进入专门修复模式。

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
- 当前轮禁止继续字段追问

#### 回复要求

包含三部分:

1. 承认
2. 降压
3. 交还主导权

推荐骨架:

- `是，我这边刚才问得有点密了。`
- `这轮我不继续追资料。`
- `你想先聊你的要求，还是你比较在意哪类人，我顺着你说。`

#### 后续约束

- complaint 命中后至少 1 轮 cooldown
- cooldown 期间不主动问字段

### B. 新增语义槽去重

#### 目标

防止“换说法重问同一件事”。

#### 推荐语义槽

- `basic_identity`
- `location`
- `education`
- `occupation`
- `income`
- `marital`
- `partner_preference_age`
- `partner_preference_location`
- `partner_preference_height`
- `partner_preference_personality`
- `contact_phone`
- `contact_wechat`

#### 规则

1. 用户近 5 轮内明确给过该语义槽，则禁止再次主动问同槽
2. 已收集完成的槽，禁止用泛化句重问
3. 若只收集了部分信息，只允许澄清，不允许重新开总类问题

#### 必须拦截的情况

当 `partner_requirement` 已非空时，默认禁止:

- `你最看重哪一点`
- `你更在意哪几点`
- `你可以先说一个最在意的匹配点`

### C. FAQ / 边界后的 bridge-back

#### 目标

支线结束后自然回主线。

#### 状态要求

FAQ / boundary 完成后记录:

- `needs_bridge_back = True`
- `last_side_topic_type = faq_photo / faq_contact / faq_process / boundary`

#### 下一轮行为

如果命中 `needs_bridge_back`:

1. 先输出一句轻桥接
2. 再进入主线字段推进

#### 示例

- `这块先这样。你现在主要在哪个城市？`
- `先不往照片这边走，你现在是在深圳这边发展吗？`

### D. 短答轻量生成层（已废弃）

#### 目标

该方案原本用于减少短答轮成本，但已因状态分叉和拟人感问题废弃。

#### 命名

- 当前不再单独设置轻量生成路由

#### 适用输入

- `男的`
- `90后`
- `深圳`
- `本科`
- `4万左右`
- `对`
- `是`
- `嗯`
- `好`

#### 轻量 prompt 组成

只保留:

1. 当前用户消息
2. 上一轮 AI 问题
3. 当前目标字段
4. 少量核心画像摘要
5. 极短风格约束

#### 不要带的内容

- 全量主 prompt
- 全量历史
- 长篇策略解释

#### 目标指标

- `prompt_chars` 降到 `800-1500`
- 短答输入 token 显著下降
- 短答耗时目标 `p95 < 4s`

### E. 删除元策略外显话术

#### 目标

降低“系统在解释自己怎么聊天”的感觉。

#### 默认清洗 / 降频的表达

- `按X来聊`
- `按这个方向来聊`
- `先不连着问资料`
- `这轮先不把资料问得太密`
- `按这个优先推进`
- `按这个优先筛`

#### 替换原则

- 用短确认替代流程说明
- 不解释策略，直接自然推进

#### 替换示例

原句:

- `好，那我们就按90后来聊。`

改成:

- `90后是吧。`
- `那年龄段我大概有数了。`

### F. 偏好已收集后的主线恢复

#### 目标

用户给了偏好后，不再原地打转。

#### 规则

如果本轮提取到了 `partner_requirement`:

1. 优先确认偏好
2. 然后切回真正缺失字段
3. 禁止再次问泛化偏好问题

#### 示例

用户:

- `同城吧`

AI:

- `好，你比较看重同城。`
- `你这边现在主要做什么工作？`

### G. 低频画像小结

#### 目标

让 AI 更像“真的记住了你”。

#### 触发条件

当这些字段收集到 4 个及以上时，可低频使用:

- 年龄 / 年龄段
- 城市
- 学历
- 收入
- 偏好

#### 示例

- `我先按你在深圳、偏同城、希望对方别超过30来理解。你这边现在做什么工作？`

#### 约束

- 一段对话最多使用 1-2 次
- 不要每轮都总结

### H. 调整字段优先级

#### 目标

让对话更接近真人节奏。

#### 推荐顺序

1. 性别
2. 年龄
3. 城市
4. 偏好轻聊
5. 学历 / 工作
6. 婚姻状态
7. 收入
8. 联系方式

#### 要求

- 收入字段后移
- 偏好只穿插一两次，不要反复开问

## 文件级实施清单

### 1. `src/modules/conversation/domain/turn_decision.py`

需要支持:

- `intent = complaint`
- `primary_move = repair_and_release`
- `response_channel = model`

### 2. `src/modules/conversation/application/process_chat_turn.py`

需要改造:

- 统一走主模型路由
- FAQ / boundary 结束后记录 `needs_bridge_back`
- complaint 命中后写入 cooldown
- 增加对应埋点:
  - `complaint`
  - `bridge_back`

### 3. `src/services/core/chat_service.py`

建议新增或扩展函数:

- `detect_complaint_or_conversation_fatigue(...)`
- `should_block_generic_preference_prompt(...)`
- `should_block_redundant_slot_ask(...)`
- `build_repair_response(...)`
- `build_bridge_back_prefix(...)`
- `sanitize_strategy_leakage_phrases(...)`
- `should_emit_profile_summary(...)`
- `build_profile_summary_line(...)`

出站前需要统一做:

- 元策略话术清洗
- complaint 轮抑制追问
- “按X来聊”频率限制

### 4. `src/services/core/dialogue_manager.py`

需要改造:

- 选择下一问前先做语义槽去重
- `partner_requirement` 已存在时，禁止再问泛化偏好句
- 调整字段优先级，收入后移
- FAQ 后支持 bridge-back
- 允许低频 profile summary

### 5. `src/services/prompts/prompts.py`

需要改造:

- 删除轻量生成 prompt 的旧设计描述，统一维护主模型提示词
- 弱化主 prompt 中会诱发“按X来聊”“不连着问资料”的指令
- complaint 场景补充修复型提示

### 6. `src/modules/profile_collection/domain/ask_tracking_service.py`

需要改造:

- 支持 complaint cooldown
- 支持语义槽级别去重，不只按字段名统计

### 7. `src/modules/profile_collection/domain/extraction_service.py`

需要改造:

将 `partner_requirement` 细分至少以下子槽:

- `partner_preference_location`
- `partner_preference_age`
- `partner_preference_height`
- `partner_preference_personality`

### 8. 用户状态 / 档案存储相关代码

需要新增轻量状态:

- `needs_bridge_back`
- `last_side_topic_type`
- `complaint_cooldown_turns`
- `recent_semantic_slots`
- `last_profile_summary_turn`

## 实施顺序

严格按这个顺序执行:

1. complaint / repair
2. 偏好去重 guard
3. 元策略话术清洗
4. FAQ bridge-back
5. 主模型短答一致性
6. 字段优先级调整
7. 低频 profile summary

原因:

- 前三项直接解决“重复问”和“像流程机”
- 中间两项解决衔接与一致性
- 最后两项是增强项

## 必补测试

### 单元测试

必须覆盖:

1. complaint 命中后进入 repair
2. complaint 命中后当前轮不再追问字段
3. 已有 `同城` 后，不再问“最看重哪一点”
4. FAQ 后回主线带 bridge-back
5. `男的 / 深圳 / 本科 / 4万左右` 仍按短答处理，但统一走主模型
6. 元策略话术被清洗
7. 连续两轮都出现“按X来聊”会被抑制

### 多轮回归用例

建议新增完整脚本覆盖:

- `你好 -> 男的 -> 90后 -> 深圳 -> 同城吧 -> 对方不要超过30岁 -> 这个是不是问太多了`

验证点:

- 不重复问偏好
- complaint 能修复
- 不再频繁出现元策略话术

## 验收标准

### 对话质量

1. 用户已给的偏好不再被同义重问
2. FAQ 回主线更自然
3. 用户抱怨时系统会修复，不继续追问

### 拟人化

1. 回复首句更多是在承接用户，而不是解释策略
2. 长对话中“按X来聊 / 不连着问资料”显著下降
3. 已知画像能低频、自然地被整合使用

### 性能

1. 短答场景保持稳定，不因分叉路由导致状态错乱
2. 不重新引入轻量生成分支
3. 不重新引入固定模板主链路

### 业务约束

1. 风险 / FAQ / 边界能力保持可用
2. 联系方式收集不突兀
3. 不因修 complaint 而破坏主线字段采集

## 给执行模型的最后提醒

1. 不要只做文案替换
2. 不要把“轻量生成”做回“固定模板”
3. 先修决策和 guard，再修风格
4. 修改后必须跑相关单测和多轮回归

这份文档是执行规格，不是建议列表。后续模型默认按此文档实现。
