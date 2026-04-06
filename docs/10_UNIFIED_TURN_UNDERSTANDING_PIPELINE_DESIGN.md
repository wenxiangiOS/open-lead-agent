# 10 统一单轮理解管线设计

## 目标

在不改变现有业务策略口径的前提下，把全项目用户输入理解统一收口到一条主链：

1. `词库信号层`
2. `语义归因层`
3. `AI 上下文消歧层`
4. `统一理解结果`

在当前版本开始，统一理解主链正式补齐下游执行步骤：

5. `上下文感知字段提取层`
6. `字段互斥裁决层`
7. `统一落库前一致性校验层`
8. `统一字段追问与恢复裁决层`

第一阶段明确保持以下逻辑不变：

- 开场白与 opening probe 策略保持现状
- 核心字段 / 中等字段推进策略保持现状
- 联系方式策略与状态机保持现状
- 收尾与结束策略保持现状

本方案只统一“这句话是什么意思”，不直接重写“下一步怎么推进”。

补充说明：

- 统一理解结果不再只服务于 turn type / subtype
- 它还必须成为字段提取的唯一上游输入
- 后续字段提取、冲突裁决、落库校验，都必须服从统一理解结果
- 不允许再出现“理解层已经知道这是联系方式回复，但字段层仍先把数字串提成年龄”的分叉执行

## 为什么要新增独立模块

当前项目中，单轮理解虽然已有 `turn_understanding_service`，但真实语义判断仍然分散在：

- `TurnUnderstandingService`
- `ChatService` 中的 FAQ / boundary / risk / contact context 判断
- `ProfileCollectionPolicy`
- 联系方式流程
- guard / resume / repair / post-process

结果是：

- 同一句输入可能在多个模块被重复定性
- 前面判断的结果可能被后面模块重新覆盖
- 理解权和策略权耦合，导致问题难定位

因此需要把“理解用户输入”做成独立模块，并让现有业务模块只消费统一结果。

## 总体设计

新增模块目录：

- `src/modules/conversation_understanding/domain/models.py`
- `src/modules/conversation_understanding/domain/lexical_signal_layer.py`
- `src/modules/conversation_understanding/domain/semantic_understanding_layer.py`
- `src/modules/conversation_understanding/domain/ai_context_disambiguation_layer.py`
- `src/modules/conversation_understanding/domain/unified_turn_understanding_service.py`

其中：

- `词库信号层` 负责高召回 signal
- `语义归因层` 负责字段级上下文理解
- `AI 上下文消歧层` 负责冲突与低置信度场景
- `统一理解服务` 负责编排三层并输出兼容旧系统的结果
- `上下文感知字段提取层` 负责在理解结果约束下产出允许进入后续流程的字段
- `字段互斥裁决层` 负责处理 `phone/wechat` 与 `age/height/weight`、`sex` 与 `partner_gender_preference` 等冲突
- `统一落库前一致性校验层` 负责最终兜底，阻止上下文不一致字段写入档案
- `统一字段追问与恢复裁决层` 负责：
  - 主字段之后还能不能顺带问 side-target
  - FAQ / 顾虑轮是否要挂起 `resume_profile_target`
  - FAQ 后确认语是否必须恢复被打断字段

## 分层职责

### 1. 词库信号层

只负责：

- 问候 signal
- FAQ signal
- 拒绝 / 边界 signal
- 联系方式 signal
- 收尾 / 退出 signal
- 风险 signal
- complaint signal

输出示例：

```json
{
  "signals": {
    "greeting": true,
    "faq": false,
    "refusal": false,
    "boundary": false,
    "contact": false,
    "closing": false,
    "risk": false,
    "complaint": false
  },
  "can_short_circuit": true,
  "short_circuit_type": "opening_greeting"
}
```

设计原则：

- 词库层是高召回，不是默认终判
- 只有低歧义场景允许短路
- 涉及字段归因、上下文归因、流程切换的场景必须继续进入语义层

### 2. 语义归因层

只负责：

- 基于当前消息、上一轮回复、当前流程阶段、已知资料、联系方式上下文，判断这句话真正的语义

输出示例：

```json
{
  "turn_domain": "profile",
  "turn_type": "field_refusal",
  "subtype": "soft_refusal_current_field",
  "target_field": "location",
  "confidence": 0.88
}
```

第一阶段为保证业务口径稳定，语义层继续复用现有 `TurnUnderstandingService` 作为主分析器，只把它封装成统一主链的一部分。

### 3. AI 上下文消歧层

只负责：

- 规则冲突
- 低置信度理解
- 泛化兜底结果复核
- 高价值歧义场景复核

从当前版本开始，AI 层不再只是“保守补丁层”，而是承担一条全项目统一原则：

**前两层没有形成稳定识别结果时，AI 必须介入。**

也就是说：

- 词库层能稳定短路的场景，可以直接通过
- 词库层不能稳定短路的，必须进入语义层
- 语义层如果仍然是模糊结果、兜底结果、冲突结果、脏槽位结果，必须升级到 AI

这条规则优先于“仅靠全局开关控制 AI 是否启用”的老逻辑。

### 4. 统一理解结果

统一理解结果是全项目唯一输入语义真源。

第一阶段为了兼容现有代码，不直接让所有模块消费新 schema，而是：

- 统一理解服务内部先得到 `UnifiedTurnUnderstandingResult`
- 再适配回现有 `TurnUnderstandingResult`

这样可以保证现有：

- `ChatService`
- `ProfileCollectionPolicy`
- `ContactCollectionService`
- `process_chat_turn`

不需要在第一阶段整体推翻重写。

### 5. 上下文感知字段提取层

这一步不再允许多个服务各自重新猜字段，必须统一收口到理解链之后。

当前实现约束：

- `SemanticUnderstandingLayer` 在 unified 主链里优先调用“不带本地字段治理”的语义入口
- 也就是 unified 主链拿到的是“原始语义结果”
- 之后统一交给独立的字段治理层做：
  - 上下文白名单
  - 显式纠正优先
  - 冲突裁决
  - 最终字段拦截

这样可以避免：

- `TurnUnderstandingService` 先本地治理一遍
- `UnifiedTurnUnderstandingService` 再治理第二遍

生产主链现在要求字段治理只在 unified 主链下游执行一次。

核心原则：

- 先得到最终 `primary_turn_type / subtype / secondary_signals`
- 再决定这轮允许提哪些字段
- 再决定这轮禁止提哪些字段

典型规则：

- 如果当前是 `contact_answer` / `in_contact_flow=True`
  - 优先提 `phone / wechat / invalid_contact_candidate`
  - 禁止 `age / age_label / height / weight` 抢纯数字串
- 如果当前是性别确认上下文
  - 允许 `sex`
  - 同时允许复合资料字段（例如 `occupation`）
  - 不允许再退化成 `connective_opening`
- 如果当前是异常值澄清上下文
  - 只允许当前异常字段
  - 不允许继续职业/收入/联系方式主线

### 6. 字段互斥裁决层

字段提取后必须进入统一冲突裁决，不允许“谁先命中谁赢”。

第一批必须固化的互斥关系：

- `phone/wechat` 与 `age/height/weight`
  - 联系方式上下文里，联系方式优先
- `sex` 与 `partner_gender_preference`
  - 自述语境优先 `sex`
  - 择偶语境优先 `partner_gender_preference`
- `education` 与 `partner_requirement`
  - 明确教育语境优先 `education`

### 7. 统一落库前一致性校验层

落库层不再承担“主判断”，只承担最后一致性兜底。

例如：

- 当前是联系方式轮，结果里如果出现 `age`，但原消息没有 `岁/年龄/今年/出生`
  - 直接丢弃 `age`
- 当前在性别确认轮，用户原文明确说了 `女生/男生`
  - 结果里如果缺失 `sex`
  - 直接补回 `sex`

### 8. 统一字段追问与恢复裁决层

这一步必须收口所有“下一句还追问什么”的判断，不允许再由多个模块各自猜主线。

当前版本明确拆成两类职责：

- `字段追问裁决`
  - 主目标字段与 side-target 统一由 `conversation_understanding` 模块里的 `FollowupPlanningLayer.choose_followup_targets()` 裁决
  - `choose_main_target()` / `choose_side_target()` 只作为内部拆分方法保留
  - `ProfileCollectionPolicy` 退化为字段覆盖、优先级、上下文评分规则库，不再自己分散落地 `main_target / side_target` 的最终选择

- `FAQ 后恢复主线裁决`
  - FAQ / 顾虑轮如果打断了字段追问，必须挂起 `resume_profile_target`
  - 下一轮如果识别到 `post_answer_reentry=True`，则不再走普通 `confirmation` 分支
  - 统一由 `FollowupPlanningLayer.resolve_resume_after_faq()` 决定是否恢复，以及恢复哪个字段
  - 一旦命中恢复字段，最终 `TurnDecision` 必须强制改写为：
    - `intent=general`
    - `primary_move=light_followup`
    - `ask_field=resume_field`
    - `prioritize_user_question=false`

工程约束：

- FAQ 后恢复主线只能在一个统一出口执行
- 恢复结果一旦确定，后续 FAQ guard / confirmation 收尾逻辑不得再次覆盖
- FAQ 回复文本不允许反向污染 `last_asked_field`
- FAQ 轮如果没有真实追问，必须保留被打断字段上下文，供下一轮恢复

### 显式纠正优先级

上下文白名单不能硬拦用户主动改正。

统一优先级顺序：

1. 风险 / 收尾硬规则
2. 显式纠正
3. 当前上下文白名单
4. 普通字段提取
5. 落库前一致性校验

也就是说：

- 当前即使在问电话
- 用户如果明确说“不是本科，是大专”
- `education` 也必须允许通过

## 新旧系统的兼容原则

### 保持不变

- `TurnUnderstandingResult` 继续作为旧系统的公共输入对象
- `ProfileCollectionPolicy` 继续决定主字段 / side-target / 联系方式 Gate
- `ContactCollectionService` 继续负责联系方式推进
- `ChatService` 继续负责编排和副作用

### 新增变化

- 所有主入口不再直接调用 `TurnUnderstandingService.analyze(...)`
- 统一改为调用 `UnifiedTurnUnderstandingService.analyze(...)`
- `TurnUnderstandingService` 退化为统一理解模块内部的语义层依赖，不再作为外部主入口

## 第一阶段接入点

第一阶段只替换理解入口，现有业务推进逻辑不变。

主要接入点：

- `src/modules/conversation/application/process_chat_turn.py`
- `src/services/core/chat_service.py`

改造要求：

1. 所有主流程分析单轮输入都走统一理解服务
2. 旧的 `turn_understanding_service` 仍保留，但只作为统一理解服务的内部依赖
3. 后续模块先继续消费旧 `TurnUnderstandingResult`，降低迁移风险

## 第二阶段执行收口

当统一理解主链稳定后，主流程继续往“orchestration-only”收口：

- `ChatService.prepare_turn_execution(...)`
  统一承接：
  - 单轮理解
  - shadow profile 构建
  - turn decision 构建
  - `quick_faq -> model` 的表达通道覆盖

- `ChatService.consume_bridge_back_prefix(...)`
  统一承接：
  - bridge_back 前缀生成
  - `needs_bridge_back` / `last_side_topic_type` 状态清理

- `ChatService.maybe_build_pre_generation_short_circuit_payload(...)`
  统一承接：
  - `age_under_limit`
  - `risk_guard`
  - `boundary_pause`
  - `withdraw_close / withdraw_retain`
  - `complaint_repair`
  这类在模型生成前即可确定的短路返回

- `ChatService.maybe_build_already_ended_payload(...)`
  统一承接：
  - 已结束会话的低信息确认
  - `conversation_ended` 状态下的固定结束回复
  这类最前置的早退路径

- `ChatService.build_generation_prompt(...)`
  统一承接 prompt 编排

- `ChatService.generate_turn_response_text(...)`
  统一承接：
  - `_call_ai(...)`
  - `no_ai` fallback
  - 生成后的基础 postprocess

- `ChatService.finalize_generated_response(...)`
  统一承接生成后的表达后处理

- `ChatService.maybe_build_preset_response_payload(...)`
  统一承接收集器直接给出 `preset_response` 时的状态更新与 payload 构造

- `ChatService.build_final_turn_payload(...)`
  统一承接最终 payload 组装，包括：
  - route meta
  - infra fail meta
  - validation meta
  - 结束场景 response 修正

- `ChatService.sync_post_delivery_state(...)`
  统一承接最终回复生成后的状态同步，包括：
  - conversation state 更新
  - profile reload
  - runtime progress counter 更新
  - terminal response policy
  - repair mode 冷却递减

- `ChatService.build_enhanced_response_to_clean(...)`
  统一承接：
  - contact validation 增强
  - AI ending response 增强

- `ChatService.process_collection_phase(...)`
  统一承接：
  - `profile_collection_coordinator.process_collection(...)`
  - `partner_requirement` 收集后的 active ask 关闭
  - collection 后的 turn decision refresh
  - contact decision 预热

- `ChatService.run_generation_collection_phase(...)`
  统一承接：
  - 文本生成
  - 字段提取与合并
  - collection phase
  - preset response 早退判断
  - 并对外返回结构化阶段耗时，保证观测不因高层收口而丢失

这一阶段的目标不是改变业务口径，而是把：

- `process_chat_turn.py` 中对内部 helper 的直接感知
- prompt 细节
- bridge_back 状态清理
- response channel override

逐步收回 `ChatService`，让 use case 更接近纯 orchestration。

## 统一结果建议 schema

第一阶段内部统一结构建议如下：

```python
UnifiedTurnUnderstandingResult(
    lexical_signals: dict[str, bool],
    lexical_short_circuit: str | None,
    semantic_result: TurnUnderstandingResult,
    ai_applied: bool,
    ai_result_used: bool,
    decision_source: str,
    notes: list[str],
)
```

说明：

- `semantic_result` 仍然复用现有结果结构
- `decision_source` 用于标记本轮最终裁决来自 lexical / semantic / ai_disambiguation
- `notes` 用于调试与观测

## 第一阶段短路规则

第一阶段只允许以下场景由词库层直接短路：

- 明确开场问候
- 明确风险输入
- 明确退出 / 收尾

以下场景即使命中词库，也必须继续进入语义层：

- 字段隐晦拒绝
- FAQ / 边界冲突
- profile partial with boundary
- 联系方式偏好切换
- 当前字段错位回答

## 全局 AI 升级策略

### 什么时候必须升级到 AI

满足任一条件，就不应视为“识别完成”，必须进入 AI 消歧：

1. `confidence < threshold`
2. 当前结果属于泛化兜底 subtype，例如：
   - `opening_clarify`
   - `connective_opening`
   - `ambiguous_short_answer`
   - `garbled_or_typo`
3. 词库有强信号，但语义层没有消费掉，例如：
   - 有 `relationship_seek`，却没有落到 `matchmaking_intent`
4. 多信号冲突，例如：
   - `faq + profile`
   - `boundary + profile`
   - `contact + refusal`
   - `greeting + relationship_seek + service_confirmation`
5. 结构化槽位出现脏值或可疑截断，例如：
   - `partner_requirement=找个男`
   - 或把性别偏好错误混进 `partner_requirement`
6. 当前结果会直接影响高价值流程切换：
   - 开场轮
   - 联系方式关键转接
   - 收尾 / withdraw
   - 核心字段是否继续追问

### AI 介入后的职责边界

AI 可以修正：

- `primary_turn_type`
- `subtype`
- `secondary_signals`
- 统一语义字段中的归一结果，例如：
  - `partner_gender_preference=男/女`
  - `partner_requirement=温柔/成熟稳重/同城...`
- 统一语义 frame 中的高层语义字段

AI 不应直接决定：

- 下一步业务状态机怎么推进
- 是否切联系方式 / 收尾 / resume
- 最终用户可见中文话术

也就是说，AI 在这条管线里的职责是**语义消歧**，不是**表达层替身**。

## 第二阶段：统一表达主链

在统一理解主链稳定后，表达层应同步收口到一条统一主链：

1. `UnifiedTurnUnderstandingService`
2. `ConversationStatePlanner`
3. `ResponsePlanBuilder`
4. `AIResponseGenerator`

其中：

- 理解层负责“用户这句话是什么意思”
- 状态机负责“下一步该做什么”
- `ResponsePlanBuilder` 负责“要表达哪些语义点”
- `AIResponseGenerator` 负责“把 plan 说成一段自然话术”

### 表达层原则

第二阶段要明确一条全项目原则：

**语义识别归代码，最终表达归 AI。**

具体来说：

- 代码可以决定：
  - `primary_turn_type`
  - `subtype`
  - `secondary_signals`
  - `resolved_slots`
  - `main_target / side_target`
  - `ack_signals`
  - `next_move`
- 代码不应继续在普通业务主链直接返回最终中文

### 为什么要补这一层

如果只统一理解，不统一表达，系统仍会出现：

- 理解已经正确
- 但 `quick_faq` / `field_prompt` / `fused_prompt` / `followup_enforce`
  继续直接拼接中文
- 最终话术仍然像模板或积木串接

所以第二阶段的目标不是“再加一点 AI”，而是把普通业务回复统一改成：

- `understanding_result`
- `response_plan`
- `AIResponseGenerator`

### 第一批表达层改造优先级

优先收口以下主路径：

1. `quick_faq` 直返链路
2. opening 复合意图回复
3. `_build_no_ai_response()`
4. `_build_policy_field_prompt()`
5. `_build_fused_*_prompt()`

这些路径的共同问题是：

- 已经拿到了足够的结构化理解结果
- 却仍由代码直接写出最终中文

### ResponsePlan 的阶段性落地方式

第二阶段不是一上来把所有模板全部删除，而是先采用“结构化 plan 约束 + AI 一次生成”的渐进方式：

1. 理解层先产出：
   - `primary_turn_type`
   - `subtype`
   - `secondary_signals`
   - `resolved_slots`
2. 状态机继续产出：
   - `main_target / side_target / next_move`
3. 表达层增加一个中间层：
   - `ResponsePlanBuilder`
4. 模型最终收到的不是代码写好的整句中文，而是：
   - 结构化理解结果
   - 结构化 response plan
   - 生成约束（避免模板化、避免重复、保持口语化）

第一批已优先应用到复合 opening：

- `opening + matchmaking_intent`
- `opening + service_confirmation`
- `opening + preference_hint`

这些场景不再允许本地 quick_faq 直返拼接，而是切到模型表达链，并通过 response plan 约束 AI 一次生成最终回复。

同一阶段也开始向字段追问迁移：

- `ask_field` 已明确的主字段追问
- `main_target + side_target` 的融合追问
- `ask_field=contact` 的联系方式推进

这类场景在模型链里不再只依赖代码提前拼好的中文问句，而是先构造结构化 response plan，再让 AI 根据：

- `ask_field`
- `side_target`
- `resolved_slots`
- `secondary_signals`

一次生成自然回复。

阶段性目标是：

- 代码继续负责“问什么”
- 模型开始接管“怎么问”

联系方式同样适用这条原则：

- 代码负责判断当前是否进入 `contact_flow`
- 代码负责判断是 `ask_phone / persuade_phone / ask_wechat / persuade_wechat`
- 最终中文表达应逐步从 `render_contact_question()` 迁移到 `ResponsePlan + AIResponseGenerator`

这样可以避免：

- 上下文有 `location + occupation` 时，代码直接套固定联系模板
- 联系方式说服和联系方式初问长期维持模板式口径

在这一步完全落稳前，允许保留现有 `_build_policy_field_prompt()` / `_build_fused_*_prompt()` 作为 fallback 或非模型路径兜底，但它们不应再是模型主链的唯一表达来源。

### ResponsePlan 的实现建议

建议新增独立结构对象，例如：

- `src/modules/conversation_response/domain/response_plan.py`
- `src/modules/conversation_response/domain/response_plan_builder.py`
- `src/modules/conversation_response/domain/response_plan_prompt_formatter.py`
- `src/modules/conversation_response/domain/profile_bridge_prompt_formatter.py`
- `src/modules/conversation_response/domain/opening_intent_prompt_formatter.py`
- `src/modules/conversation_response/domain/prompt_assembly_service.py`
- `src/modules/conversation_response/domain/ai_response_generator.py`

用于承载：

- `mode`
- `ack_items`
- `next_move`
- `ask_field`
- `side_target`
- `resolved_slots`
- `secondary_signals`
- `constraints`

这样可以避免“response plan 只是另一段 prompt 字符串”的退化实现。  

其中建议明确分层：

- `ResponsePlan` 负责承载结构化表达计划
- `ResponsePlanBuilder` 负责把 `turn_decision + understanding_result + profile` 组装成 plan
- `ResponsePlanPromptFormatter` 负责把 plan 序列化成模型提示片段
- `ProfileBridgePromptFormatter` 负责把 bridge 约束序列化成模型提示片段
- `OpeningIntentPromptFormatter` 负责把 opening intent detection 约束序列化成模型提示片段
- `PromptAssemblyService` 负责按固定优先级把多段 instruction 组装进最终模型 prompt
- `AIResponseGenerator` 负责承接已装配完成的 prompt，并执行最终模型生成调用
模型最终收到的生成约束，应该来自 `ResponsePlan` 的结构化序列化，而不是由多个 helper 临时拼接中文说明。

在主流程编排上，建议再保持一条阶段性边界：

- `process_chat_turn.py` 不直接逐条感知 `profile_bridge / response_plan / opening_intent_detection` 的 prompt 细节
- prompt 的最终准备应收口到一个统一入口，例如 `ChatService.build_generation_prompt(...)`
- `PromptAssemblyService` 负责固定优先级的 instruction 装配，但主流程只消费“已装配完成的生成 prompt”

同理，生成后的表达后处理也应逐步收口：

- `process_chat_turn.py` 不直接逐条串接几十个清洗 / guard / followup helper
- 这类逻辑应统一收口到一个后处理入口，例如 `ChatService.finalize_generated_response(...)`
- 主流程只消费“已完成后处理的最终回复 + delivery 状态”

与之对应，中间过程也建议分层收口：

- 模型原始回复的 opening intent 解析、style stabilize、profile bridge rewrite，可统一收口到例如 `ChatService.postprocess_generated_ai_response(...)`
- 模型回复后的字段提取、规则兜底、确认分类 fallback，可统一收口到例如 `ChatService.extract_and_merge_generated_fields(...)`
- 收集结果落库后的 shadow profile 重算、turn decision 刷新、followup 修正，可统一收口到例如 `ChatService.refresh_turn_decision_after_collection(...)`

这样 `process_chat_turn.py` 逐步只承担 orchestration，不再直接感知大量表达层和提取层内部 helper。

### 第二阶段当前分组视图

当前阶段建议把 `process_chat_turn.py` 看到的 `ChatService` 入口，收敛成 4 组：

1. 前置准备
   - `ChatService.maybe_build_already_ended_payload(...)`
   - `ChatService.prepare_turn_execution(...)`
   - `ChatService.maybe_build_pre_generation_short_circuit_payload(...)`
   - `ChatService.maybe_build_quick_faq_payload(...)`
   - `ChatService.consume_bridge_back_prefix(...)`

2. 生成与收集
   - `ChatService.build_generation_prompt(...)`
   - `ChatService.run_generation_collection_phase(...)`
   - 其内部继续统一承接：
     - `generate_turn_response_text(...)`
     - `extract_and_merge_generated_fields(...)`
     - `process_collection_phase(...)`
     - `maybe_build_preset_response_payload(...)`

3. 生成后表达处理
   - `ChatService.build_enhanced_response_to_clean(...)`
   - `ChatService.finalize_generated_response(...)`
   - `ChatService.sync_post_delivery_state(...)`

4. 最终交付
   - `ChatService.build_final_turn_payload(...)`
   - `ChatService.build_error_response(...)`

阶段性目标是让 `process_chat_turn.py` 最终只保留：

- 阶段调度
- 观测打点
- 成功 / 失败返回

而不再直接感知：

- prompt 拼装细节
- AI 生成细节
- collection 刷新细节
- 表达后处理细节
- payload/meta 组装细节

这也是第二阶段的一个明确验收标准：

- `process_chat_turn.py` 不再直接调用 `chat_service._...`
- `process_chat_turn.py` 只消费 `ChatService` 的公开阶段入口

同时，承载这些阶段结果的结构对象，也应逐步从 `ChatService` 大文件本体中拆出，收口到独立模型模块，例如：

- `OpeningIntentSignal`
- `TurnExecutionPreparation`
- `AlreadyEndedPreparation`
- `CollectionPhaseOutcome`
- `GenerationCollectionPhaseOutcome`

这样可以避免“统一入口已经抽出来，但阶段数据结构仍然全部堆在 `ChatService` 顶部”的中间态长期固化。

同样地，阶段入口本身也应逐步按职责拆成 helper/service，而不是继续全部堆在 `ChatService` 一个大类里。当前阶段可优先按以下顺序下沉：

- `ChatServicePreparationService`
  承接：
  - `prepare_turn_execution(...)`
  - `consume_bridge_back_prefix(...)`
  - `maybe_build_pre_generation_short_circuit_payload(...)`
  - `maybe_build_quick_faq_payload(...)`
  - `maybe_build_already_ended_payload(...)`

- `ChatServiceGenerationService`
  承接：
  - `generate_turn_response_text(...)`
  - `process_collection_phase(...)`
  - `run_generation_collection_phase(...)`

- `ChatServiceDeliveryService`
  承接：
  - `build_enhanced_response_to_clean(...)`
  - `sync_post_delivery_state(...)`
  - `build_final_turn_payload(...)`

- `ChatServiceFinalizeService`
  承接：
  - `finalize_generated_response(...)`
  当前阶段内部可继续按 4 段组织：
  - 初始 delivery guard
  - 非可投递 fallback
  - followup / handoff enrichment
  - bridge 与最终 delivery

第三阶段开始后，`followup / handoff enrichment` 已进一步下沉到：

- `ChatServiceFollowupService`

当前边界变成：

- `ChatServiceFinalizeService` 负责编排 finalize 阶段四段流程
- `ChatServiceFollowupService` 负责中间最密集的 followup / handoff / resume enrichment

继续细拆后，`ChatServiceFollowupService` 内部再按子领域下沉到：

- `ChatServiceFieldFollowupService`
- `ChatServiceContactFollowupService`

随后又继续按规则类型拆分为：

- `ChatServiceFieldTransitionService`
- `ChatServiceFieldGuardService`
- `ChatServiceContactHandoffService`
- `ChatServiceContactGuardService`

同时，部分 `resume / contact completion` 类 guard 也可继续从 `ChatService` 本体下沉到独立 helper，例如：

- `ChatServiceResumeGuardService`

另外，纯文本策略工具也可继续从 `ChatService` 本体抽离，例如：

- `ChatServiceTextPolicyService`
- `ChatServiceContactTextService`
- `ChatServiceAckRenderService`
- `ChatServiceBridgeTextService`
- `ChatServiceContactValidationTextService`
- `ChatServiceEndingStateService`
- `ChatServiceResponseCleanupService`
- `ChatServiceSummaryHelperService`

这类 helper 也适合继续承接：

- contact push marker 判断
- 低信息回复判断
- 重复 ack 折叠
- `response_already_acks_field / response_already_absorbs_location_context` 这类响应文本判断
- `response_already_acknowledges_short_answer` 这类短答吸收判断
- 联系方式收集成功确认、联系方式后续追问、微信/电话 fallback 这类纯文案 helper
- `preference / occupation / marital_status / age` 这类 ack 渲染 helper
- `bridge_back_prefix` 这类桥接前缀 helper
- 联系方式校验重试 fallback、连续无效输入 close response 这类校验文案 helper
- 结束态下的 contact completion / no-contact completion 这类轻量状态与固定结束话 helper
- `already_ended / both_rejected` 这类固定 ending response helper
- `strip_broken_edge_fragments / compress_multi_action_response / normalize_redundant_confirmation_phrasing / soften_awkward_age_question` 这类响应清洗 helper
- `looks_like_truncated_response / is_delivery_viable` 这类投递前文本质量判断 helper
- `extract_partner_requirement_hint / build_profile_summary_line` 这类摘要与偏好提示 helper

轻量消息语义判断也可独立成 helper，例如：

- `ChatServiceMessageSignalService`

这类 helper 适合继续承接：

- acknowledgement-only 判断
- short-answer 判断
- withdraw / resume_profile_collection 这类轻量消息语义判断
- `has_any_valid_contact` 这类轻量状态判断

后续可继续按同样模式拆出：

- 更细粒度的 followup / guard sub-service

这样 `ChatService` 保留统一公开入口和 orchestration 角色，但不再继续吸纳所有阶段实现细节。

对于开场前半段的短路返回，也建议逐步收口：

- `already_ended / age_under_limit / risk_guard / quick_faq / boundary_pause / withdraw / complaint_repair` 这类分支，不应在 `process_chat_turn.py` 里重复手写“更新状态 -> reload profile -> build payload”
- 这类重复流程可统一收口到类似 `ChatService.build_short_circuit_payload(...)` 的入口
- 主流程只负责决定“为什么短路、走哪个 route”，不负责重复拼装短路返回的状态更新和 payload 构造

阶段性边界建议再明确一条：

- 表达层相关的 AI 调用（最终回复生成、style rewrite、profile bridge rewrite）应优先统一收口到 `AIResponseGenerator`
- 仍允许少量语义层专用 AI 调用单独保留，例如确认分类 fallback；这类调用应单独封装为语义 helper/classifier，不应和普通回复生成混用

### quick_faq 的阶段性约束

在第二阶段完全落地前，先加一条阶段性约束：

**复合业务场景不得走 `quick_faq` 规则直返。**

例如：

- `opening + matchmaking_intent`
- `opening + service_confirmation`
- `opening + relationship_seek + preference`
- `faq_concern + service_confirmation_mid`

这些场景应直接切到模型表达链，而不是继续使用本地模板或多段拼接。

进一步收紧后，`quick_faq` 只保留白名单场景：

- 纯问候
- 纯单意图 FAQ

以下情况即使当前 `response_channel` 初判为 `quick_faq`，也应强制切到模型表达：

- 任意 opening 复合业务意图
- 任意带 `resolved_slots` 的 quick 场景
- 任意联系方式推进/确认/解释场景
- 任意 FAQ + 资料 / FAQ + 服务确认 / FAQ + 联系方式的混合场景

### no_ai 本地兜底约束

`_build_no_ai_response()` 只应作为：

- AI 不可用
- 基础可用性保护

下的保底路径，而不是普通业务表达主链。

因此它也应遵守两条约束：

1. 只输出单条、紧凑、可读的本地兜底回复
2. 不允许再做“服务确认 + 偏好承接 + 自我介绍”这类多段模板拼接

也就是说，`no_ai` 路径可以保留有限本地表达，但只能是最小可用 fallback，不应继续承担复杂业务话术编排。

### 模型回复后的后处理约束

第二阶段还需要明确一条后处理规则：

**模型已经生成自然回复后，后处理不应轻易再用模板问句覆盖它。**

具体来说：

- `enforce_*followup`
- `handoff_to_contact_*`
- `natural_completion_transition`

这些后处理如果确实要兜底，也只能在“模型回复明显是低信息空转”时才允许用本地 followup 覆盖。

例如：

- `你继续说，我先顺着听。`
- `顺着往下了解。`
- `先顺着聊。`

这类低信息回复可以被结构化 followup 兜底。

但如果模型已经给出一段有信息密度、且自然承接用户语义的回复，即使没完全问到目标字段，也不应马上用模板问句把它洗掉。  
否则会造成：

- 模型表达已经自然
- 后处理又回退成模板化追问

因此第二阶段的具体约束是：

- `handoff_to_contact_*`
- `handoff_to_pending_target_*`
- `enforce_active_target_followup`
- `enforce_missing_sex_followup_after_preference`
- `enforce_contact_gate_followup`

这类“强推进”后处理，也应先判断当前模型回复是否属于低信息空转。  
如果模型已经给出一段自然且有信息密度的回复，不应为了补一个字段或切一个目标，就立即回写为本地模板问句。

### dialogue_expression_service 的阶段性角色

第二阶段里，`dialogue_expression_service.py` 不应再作为模型主链的主要表达来源。

更具体地说：

- 它可以继续承担：
  - fallback/helper
  - 非模型路径兜底
  - 软确认提示的局部工具能力
- 它不应继续承担：
  - 模型重写时的主表达种子
  - 模型主链里最终问法的唯一来源

模型重写如果需要一个 seed，也应优先使用：

- 中性 followup seed
- 结构化 response plan

而不是直接把 `render_field_question()` 生成的模板问句当成主表达种子。

同样地，模型后处理里的这些分支：

- `enforce_active_target_followup`
- `enforce_missing_sex_followup_after_preference`
- `handoff_to_contact_*`
- `handoff_to_pending_target_*`

如果确实还需要给模型一个 followup seed，也应优先使用中性 followup seed，而不是直接回退到 `render_field_question()` / `_build_policy_field_prompt()` 的模板问句。

这条原则也应逐步扩展到：

- `resume`
- `post_contact_resume`
- `no_ai` 下的继续追问兜底

当前阶段的落地口径应进一步收紧为：

- 模型主链相关的 `resume`
- `service_confirmation_resume`
- `post_contact_resume`
- `repeated-field correction`
- `profile bridge fallback`
- `interleaving followup` 的模型兜底路径

这些路径如果需要继续推进字段，也应优先回 `中性 followup seed`，而不是直接回 `_build_policy_field_prompt()`。

如果场景本身属于“主字段 + side-target”的交错追问，模型链也应优先使用：

- `中性交错 seed`
- `ResponsePlan`

而不是直接复用 `_build_interleaving_followup()` 的本地融合问句。

阶段性落地上，`_build_interleaving_followup()` 应逐步收缩到：

- `no_ai`
- 纯本地 fallback
- 极少数必须本地兜底的继续追问

而模型相关的 `profile bridge fallback` / `active target followup` / `repeated-field correction` / `core streak interleaving`，应优先切到 `_build_interleaving_seed_for_model_rewrite()`。

对于 `contact`，阶段性目标也应一致：

- 模型主链优先走 `ResponsePlan + AIResponseGenerator`
- 如果确实需要本地兜底，只保留 `单条 contact fallback`

也就是说，`render_contact_question()` 不再作为模型主链默认表达出口，而主要保留给：

- 非模型路径
- 本地 fallback
- helper 层兼容

`_build_policy_field_prompt()` / `render_field_question()` 保留的主要范围，应逐步收缩到：

- 真正的本地 fallback
- 非模型路径兜底
- `dialogue_expression_service` 的 helper 能力

而不再承担模型主链表达层的默认出口。

实现上，可以进一步把：

- `_build_policy_field_prompt()`

收口成：

- `_build_local_field_fallback_prompt()` 的轻包装

从命名和职责上明确它属于本地 fallback/helper，而不是模型主链表达层。

也就是说，如果这些路径只是为了给下一步追问一个 seed，优先也应使用中性 followup seed，而不是继续把模板问句当作默认主表达。

AI 不应无约束地改写：

- 已明确确认的高风险结果
- 已明确确认的联系方式原始值
- 已确认无歧义的基础画像字段

### 推荐环境变量

- `UNIFIED_TURN_AI_DISAMBIGUATION_ENABLED`
- `UNIFIED_TURN_AI_CONFIDENCE_THRESHOLD`

说明：

- 上述环境变量仍然保留，用于控制“普通低置信度 / 普通冲突”是否启用 AI
- 但对“前两层未识别完成”的强制升级场景，不应再完全依赖保守开关

## Opening / Profile / Contact 的统一语义 frame 方向

后续阶段不再只依赖单个 subtype，而是逐步引入结构化语义 frame。

例如 opening：

```python
OpeningSemanticFrame(
    has_greeting: bool,
    has_relationship_seeking_intent: bool,
    has_service_confirmation: bool,
    has_faq: bool,
    has_boundary: bool,
    relationship_goal: str | None,
    partner_gender_preference: str | None,
    service_request_strength: str | None,
    provided_profile_fields: list[str],
)
```

设计目标：

- 开场轮不再只是“整句命中一个 subtype”
- 而是先抽成分，再做组合决策
- 回复层最终也应消费 frame，而不是只消费单个 subtype

## 后续模块只消费，不再重判

这是本方案的核心约束。

含义：

- 语义定性只能由统一理解模块完成
- 业务模块只能根据结果决定动作
- 不允许业务模块再次判断“这句话到底是什么”

第一阶段由于历史包袱仍允许少量兼容性重判逻辑存在，但新的理解入口已经统一。后续阶段要逐步清理这些旧逻辑。

同时，从当前版本开始新增一条约束：

- 业务模块不得把“泛化兜底结果”当作真正识别完成
- 若统一理解模块标记为需要 AI 升级，业务模块不得绕过

## 两阶段落地计划

### 第一阶段：统一理解入口

目标：

- 新增独立理解模块
- 接管主流程理解入口
- 保持现有业务策略不变

完成标准：

- `process_chat_turn` 与 `ChatService` 主入口均改走统一理解模块
- 现有业务动作逻辑不大改
- 可通过日志看见 lexical / semantic / ai 选择信息

### 第二阶段：清理重复重判

目标：

- 逐步删掉 `ChatService`、guard、contact、post-process 中重复的语义判断
- 让后续模块完全只消费统一理解结果

## 当前版本落地范围

本次落地属于第一阶段，并开始进入“全局 AI 升级策略”的早期落地：

- 已新增独立统一理解模块
- 已切换主入口到新模块
- 已保留现有业务逻辑
- 已引入 AI 消歧层
- 已开始把 opening 等高价值未识别完成场景升级到 AI

未在本次强推的内容：

- 全面清理历史重判逻辑
- 全面对 `Policy` / `Contact` / `Ending` 做状态机统一改造

## 成功标准

本方案成功的标志不是“业务逻辑大改”，而是：

1. 全项目主流程都先走统一理解模块
2. 同类输入的定性口径统一
3. 前两层未识别完成的场景会被统一升级到 AI，而不是直接落入业务层
4. 开场白、核心/中等字段、联系方式逻辑保持当前产品行为
5. 后续迭代可以在新模块中持续增强识别能力，而不需要在各业务模块到处补规则
