# 09 单轮优先级策略层设计

## 0. 文档定位

本文件只解决一个问题：

`同一句话里同时出现多种信号时，系统到底先处理什么。`

它不替代：

- `08_OPENING_GUARD_DESIGN.md` 的开场保护设计
- `10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md` 的统一理解与写库架构

它负责定义：

- 单轮优先级排序
- 主任务与被压制任务
- 回答/确认/记录/追问模式
- ChatService 应如何消费统一理解结果

---

## 1. 设计目标

目标只有三个：

1. 把分散在 `turn_understanding_service / chat_service / profile_collection_policy / contact flow` 里的优先级判断收口到一个模块。
2. 让“疑问 + 联系方式 + 资料 + 择偶要求 + 关键确认”这类复合输入有稳定且可解释的处理顺序。
3. 让优先级成为统一理解产物，而不是回复阶段再临时猜一次。

---

## 2. 设计原则

### 2.1 单一决策入口

- 优先级只由 `TurnPriorityPolicy` 产生。
- 其他模块不再各自定义“这轮先答疑还是先收资料”的排序规则。

### 2.2 识别和决策分离

- 统一理解负责识别：`risk / faq / contact / core fields / preference / pending confirmation`
- 优先级策略层负责排序：谁是本轮主任务，谁被压制

### 2.3 决策可回放

策略输出必须带：

- `primary_task`
- `priority_level`
- `decision_reason`
- `suppressed_tasks`
- `response_mode`

这样线上日志与样本回放能直接解释“为什么先答收费，没先追电话”。

---

## 3. 六级优先级（当前正式版）

### 3.1 P1 风险/合规硬约束

包括：

- `risk_guard`
- `closing_exit`
- `refusal_boundary_complaint`

行为：

- 直接停止资料推进
- 禁止联系方式推进
- 禁止中等字段推进
- 回复模式以 `answer_only / hold_only` 为主

### 3.2 P2 用户显式问题

包括：

- `fee`
- `how_match`
- `contact_why`
- `info_collection_why`
- `clarification`
- `timeline`
- `reliable`
- `privacy`
- 以及其余 `FAQ_RESPONSE_RULES` 中定义的问题意图

行为：

- 优先答问题
- 若同轮还有资料/联系方式/择偶偏好，则进入 `answer_then_resume`
- 当轮禁止切联系方式和中等字段主动追问

### 3.3 P3 关键状态确认

包括：

- `divorce_confirmation_pending`
- `pending_sex_confirmation`
- `pending_birth_year_bucket`

行为：

- 主任务变为 `status_confirmation`
- 锁定字段确认，不切联系方式
- 只在当前轮明显已经完成确认时才释放锁

### 3.4 P4 联系方式写入

包括：

- `contact_provided`
- `contact_preference_switch`
- 联系方式字段命中：`phone / wechat / contact`

行为：

- 记录与校验优先
- 不强制同轮追另一种联系方式
- 不覆盖更高优先级任务

### 3.5 P5 核心资料字段

包括：

- `sex`
- `age`
- `location`
- `education`
- `occupation`
- `contact`（仅从业务分层看属于核心；若同轮出现真实联系方式，实际由 P4 接管）

行为：

- 当前轮没有更高优先级时，主线继续推进核心资料

### 3.6 P6 择偶偏好字段

包括：

- `partner_requirement`
- `partner_gender_preference`
- `partner_pref_*`

行为：

- 只在前五层没有更高优先级时才作为本轮主任务

---

## 4. 模块设计

新增模块：

- `src/modules/conversation_understanding/domain/turn_priority_policy.py`

输出结构：

- `TurnPriorityDecision`

字段建议：

- `primary_task`
- `priority_level`
- `decision_reason`
- `response_mode`
- `suppressed_tasks`
- `locked_field`
- `prioritized_question_intent`
- `collection_tier`
- `allow_contact_target`
- `allow_medium_target`
- `prioritize_user_question`
- `defer_complementary_contact`

---

## 5. 输入与输出

### 5.1 输入

- `TurnUnderstandingInput`
- `TurnUnderstandingResult`
- `TurnPersistencePlan`

说明：

- 不直接读原始下游状态机
- 不直接调用回复生成器
- 只消费统一理解域已产出的结构化结果

### 5.2 输出

优先级策略输出后，需要挂到：

- `TurnUnderstandingResult.priority_decision`
- `TurnDecision.priority_*`

这样：

- 统一理解日志能看到优先级
- ChatService 决策日志也能看到优先级

---

## 6. 主链路接入方式

### 6.1 UnifiedTurnUnderstandingService

接入点：

- 在 `semantic_frame + persistence_plan + field_derivations` 完成后
- 调用 `TurnPriorityPolicy.decide(...)`
- 将结果挂到 `TurnUnderstandingResult.priority_decision`

原因：

- 这时已经拿到稳定的结构化字段、pending/provisional/accepted 分流结果
- 比只看 `primary_turn_type` 更接近真实业务意图

### 6.2 ChatService

消费方式：

1. 先读 `understanding.priority_decision`
2. 再决定：
   - 是否答疑优先
   - 是否锁定状态确认
   - 是否阻止切联系方式
   - 是否压制中等字段
3. 字段选择仍可继续复用 `ProfileCollectionPolicy`

边界：

- `TurnPriorityPolicy` 决定“这一轮先干什么”
- `ProfileCollectionPolicy` 决定“如果这一轮要推进资料，下一个字段问谁”

---

## 7. 行为规范

### 7.1 FAQ 混合轮

示例：

`深圳龙华在编教师，可以直接电话联系135...，怎么收费呢`

要求：

- `primary_task = user_question`
- `suppressed_tasks` 至少包含 `contact_record`
- `response_mode = answer_then_resume`

### 7.2 联系方式混合轮

示例：

`我在深圳做老师，找本科男生，可以直接联系135...`

要求：

- `primary_task = contact_record`
- 记录联系方式，但不强推另一联系方式
- 核心资料和偏好作为被压制任务保留

### 7.3 关键确认锁轮

示例：

- profile 已是 `离异`
- `divorce_confirmation_pending = true`

要求：

- `primary_task = status_confirmation`
- `locked_field = marital_status`
- 未明确答复前，不切联系方式

---

## 8. 与 10 号文档的关系

`10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md` 继续负责：

- 统一理解协议
- 字段状态机
- persistence plan
- 异步 backfill
- 写库门控

本文件负责：

- 单轮优先级路由
- 统一理解结果如何进入回复决策层

一句话：

`10 管“理解与写库”，09 管“这一轮先做什么”。`

---

## 9. 实施顺序

1. 新增 `TurnPriorityPolicy` 与 `TurnPriorityDecision`
2. 接入 `UnifiedTurnUnderstandingService`
3. 接入 `ChatService` 主决策链
4. 给 `TurnDecision` 增加优先级观测字段
5. 补齐单测：纯 FAQ、FAQ 混合、联系方式混合、关键确认、风险优先
6. 回归通过后，删除散落的旧优先级分支

---

## 10. 验收标准

必须满足：

1. 混合 FAQ 场景稳定先答疑
2. `divorce / sex / age bucket` 确认链不再被联系方式或偏好打断
3. 同轮提供联系方式时，不再强制补追另一联系方式
4. ChatService 决策日志能直接看到优先级结果
5. 新策略与统一理解输出一致，不再出现“理解层一个排序、回复层另一个排序”

---

## 11. 最终结论

应当做成单独模块，但必须放在统一理解域内部做“收口层”，不能再起一套平行体系。

最终结构是：

- `08` 管开场保护
- `09` 管单轮优先级策略
- `10` 管统一理解与写库架构
