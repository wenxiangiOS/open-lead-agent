# 10 统一单轮理解管线设计（质量优先最终版）

## 0. 文档定位

本文件是统一理解主链的**架构规范**，用于定义：

- 唯一语义真源
- 唯一写库计划
- 字段状态机
- 写库门控与并发保护
- 时延与稳定性策略
- 可量化验收标准

说明：

- 本文替换旧版中不完整/不可执行部分。
- 实施进度不再放在本文件，进度单独维护在 rollout 文档。
- 单轮优先级路由细则不在本文展开，统一维护在 `09_TURN_PRIORITY_POLICY_DESIGN.md`。

---

## 1. 总目标（不另起体系，做收口增强）

目标保持不变：

`全项目只保留统一理解域作为正式语义解释入口。`

增强后的硬目标：

1. 高风险字段脏写率目标 `0`
2. AI 成功解释后，后续模块不再解释原文
3. 回退路径不再拥有高风险字段正式写库权
4. 回复时延与质量并行，避免理解阻塞导致长尾超时

## 1.1 当前实施口径（2026-04-15 补充）

当前统一理解优化仍处于过渡态，但主链边界必须明确：

1. `UnifiedTurnUnderstandingService` 是唯一正式理解入口，也是唯一正式决策主脑
2. `TurnUnderstandingService` 仍保留，但当前定位只能是 helper / fallback library，不再允许作为第二个主脑独立决定最终 turn intent
3. 当前阶段允许新旧并存，但不允许“双重决策并存”
4. 同步 AI 结构化理解仍可保留，但定位改为“增强器”，不能再成为主链是否听懂用户的唯一依赖
5. 用户体验目标不是“每轮一次性抽满全部字段”，而是：
   - 明显核心字段尽量稳
   - AI 失败时不要暴露“没听懂”
   - 缺失字段用自然补问收口

---

## 2. 核心原则（保留）

### 2.1 唯一语义真源

- `TurnSemanticFrame` 是唯一语义真源
- `resolved_slots/resolved_field_evidence` 仅是 compat 投影

### 2.2 唯一写库计划

- `TurnPersistencePlan` 是唯一正式写库计划
- 写库阶段不得再从 `user_message` 派生新字段
- 下游消费规则：存在 `persistence_plan` 时只消费 `accepted_fields(committed)`；
  `provisional/pending_confirm` 仅用于追问与异步补写，不得当作正式值

新增硬约束：

- `source_channel=ai` 且 `write_mode=direct_write` 的 observation，一旦通过字段格式校验并生成 `accepted(committed)`，必须直接进入主档
- 写库阶段禁止再用 regex / fallback / extraction 重新判断“这是本人信息还是择偶要求”
- 允许阻止正式写库的原因只剩：
  - 字段值本身不合法
  - 和现有稳定值冲突
  - CAS 版本保护失败
  - AI 自己输出了 `soft_confirm`

### 2.3 原文只解释一次

- 统一理解域解释原文
- 下游仅做：校验、冲突处理、持久化执行、回复规划、展示格式化

补充说明：

- “校验”只允许检查 schema/type/range/format，不允许改写 `field/scope`
- “冲突处理”只允许基于新旧 profile 值做确认，不允许回头重读原文
- `pre_generation_resolution`、contextual short reply backfill、derived compat 字段都不是正式语义真源，不能越权追加 committed 写库计划

### 2.4 fallback 受限

- 仅 AI 缺失/失败时可触发 fallback
- fallback 输出也必须进入统一 `TurnSemanticFrame` 协议
- fallback 不得直接提交高风险字段到 committed

---

## 3. 字段分层与风险分组（最终定稿）

## 3.1 业务优先级分层

- 核心字段：`sex, age, location, education, occupation, contact`
- 中等字段：`marital_status, partner_requirement, monthly_income`
- 低优字段：`last_name, height, weight`

## 3.2 风险分组（写库风控）

高风险字段（脏写率目标 0）：

- `occupation, age, monthly_income, contact, partner_requirement, sex`

说明：

- “核心字段”是业务价值分层
- “高风险字段”是误写代价分层
- 两套维度并行，不冲突

---

## 4. 统一输出协议（TurnSemanticFrame）

每条 `FieldObservation` 必须包含：

- `field`
- `value`
- `normalized_value`
- `scope`（`self/partner/contact/faq/meta/mixed`）
- `owner`
- `evidence_text`
- `evidence_span`
- `confidence`
- `write_mode`（`direct_write/soft_confirm`）
- `source`

硬约束：

- 无 `scope` 不允许进入正式写库决策
- 数字字段必须做局部证据绑定，不允许裸数字归属

---

## 5. 两阶段语义提交（质量优先）

## 5.1 阶段 A：同步路径（低延迟）

输出：

- `semantic_frame`
- `persistence_plan`

行为：

- AI `direct_write` 且字段归属明确时，允许直接进入 `committed`
- 其余进入 `provisional` 或 `pending_confirm`
- 不阻塞回复

## 5.2 阶段 B：异步补全（高质量）

行为：

- 完整语义补全后执行冲突合并
- 触发状态提升（`provisional -> committed`）
- 全程受版本保护与覆盖规则约束

### 5.3 密集自我介绍同步理解（新增）

适用场景：

- 用户一上来发长句，混合了本人资料、择偶要求、联系方式、FAQ
- 当前轮如果只靠 fallback，很容易出现“明明说了还继续问”的傻感

执行规则：

- 统一理解先判定 `turn_mode=dense_intro`
- 命中后，如果 `UNIFIED_TURN_SYNC_AI_DENSE_INTRO_ENABLED=1`：
  - 规则层覆盖不足时，本轮同步 AI 触发原因为 `sync_dense_intro`
  - 规则层已经稳定覆盖核心自我信息，且 partner/contact 信号也已入槽时，直接走 `dense_intro_async_backfill_only`
  - 对于“长句自介 + 联系方式 + 明显择偶意图”这类高信息量开场，即使 partner 子槽尚未在前置语义层完全投影，只要本人资料已稳定覆盖，也应优先走 `dense_intro_async_backfill_only`
  - 对于“长句自介 + 收费问题”这类 mixed FAQ，只要规则层已经稳定覆盖本人资料，且文本里仍有明显择偶/资料信号，也不应仅因 `怎么收费` 继续阻塞主链同步 AI
- `dense_intro` 专用超时读取 `UNIFIED_TURN_SYNC_AI_DENSE_INTRO_TIMEOUT_SECONDS`
- 但主链实际同步阻塞仍受 `UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS` 约束
- 即：当前轮实际等待时长 = `min(UNIFIED_TURN_SYNC_AI_DENSE_INTRO_TIMEOUT_SECONDS, UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS)`
- 如果只是为了排障/离线验证想真的等到更长时间，需要同时抬高 `UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS`

目标：

- 让长句高信息量输入在“当前轮”就完成理解，当前轮回复不要回头问已经明确给出的字段
- 异步 backfill 继续保留，但只负责补细节和补档，不负责修正当前轮已经发出的问句

### 5.4 当前轮不重复追问摘要（新增）

统一理解完成后，需要把以下摘要同步到 `last_semantic_summary`：

- `turn_mode`
- `observed_fields`
- `pending_fields`
- `resume_target`
- `no_reask_fields`

约束：

- `no_reask_fields` 的语义只是“当前轮/下一轮暂时不要主动再问”，不是“字段已经 committed”
- ChatService 决策阶段必须先把这份摘要注入 shadow profile，再决定下一问
- `pending_birth_year_bucket` 这类明确待确认状态优先级更高，不能被 `no_reask_fields=["age"]` 直接压掉

### 5.4.1 AI 成功后的 fallback 融合补填（新增）

- 当 `ai_structured_extraction` 成功时，不再把 fallback 完全丢弃
- 当前阶段先做“缺失字段补填”：
  - 如果某个 `field + scope` 已经由 AI 给出，则保留 AI 结果，不用 fallback 同字段覆盖
  - 如果某个 `field + scope` AI 没给，但 fallback 投影里有，则把 fallback observation 补进同一份 semantic frame
- 这一步的目标是让 AI 和 fallback 从“二选一”变成“AI 主体 + fallback 补缺”
- 同字段冲突目前只放开“可证明更优”的 refinement：
  - 例如 `深圳 -> 深圳南山`、`硕士 -> 港硕`
  - 或 authoritative direct observation 对 AI 粗值的纠偏，例如 `外贸行业工作 -> 外贸`
- 更宽的同字段冲突合议仍暂缓，避免一次性改动过大

### 5.5 同步 AI 超时后的主链降级（新增硬规范）

适用场景：

- `sync_dense_intro`
- 资料回答轮
- 混合长句：本人资料 + 择偶要求 + 联系方式 + FAQ

硬规则：

1. 同步 AI 一旦超时、报错或返回不可用结果，主链必须留在 unified pipeline 内继续完成降级，不允许直接把整句视为“未理解”
2. 降级顺序固定为：
   - 先做长句切块
   - 再做块级高置信字段抽取
   - 再做自然摘要收口
   - 最后生成 `no_reask_fields`
3. 长句切块最少要覆盖：
   - `self_profile_chunk`
   - `partner_requirement_chunk`
   - `contact_chunk`
   - `faq_chunk`
   - `soft_trait_chunk`
4. `no_reask_fields` 只能来自显性硬证据，不得来自模糊摘要
5. 当前轮回复只允许消费：
   - 已确认硬字段
   - 当前轮自然摘要
   - 当前最明显的用户问题
6. AI 超时后，系统仍必须避免回头问已经明确给出的字段，例如：
   - `女生`
   - `94年`
   - `深圳南山`
   - `港硕`
   - `微信联系我 134...`

字段分流约束：

- 硬字段：`sex, age, location, education, occupation, marital_status, monthly_income, contact`
- 软画像：例如 `E人、喜欢做饭旅游、感情经历简单、原生家庭幸福`
- 择偶摘要：例如 `90后男生、同在深圳发展、积极阳光、三观正`

目标：

- AI 成功时提高精度
- AI 失败时保证主链不变傻
- 回复层先承接重点，再补 1 个关键问题，而不是机械重问

补充说明：

- 若业务验收允许 `120s` 内回复，`UNIFIED_TURN_SYNC_AI_DENSE_INTRO_TIMEOUT_SECONDS` 仍可以保留较宽松的质量上限
- 但这不代表主链可以真的卡满该值；主链当前轮仍必须受 `UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS` 控制
- 这时主链的关键不是“10 秒内一定返回”，而是“单次坏调用不要拖满 45 秒，连续异常也不要每轮都卡满超时”
- 因此统一理解主链需要额外具备同步 AI 熔断能力：
  - 仅对 `timeout / connection / read` 类底层失败计数
  - 连续达到阈值后，短时间内跳过同步 AI
  - 主链立即回落到增强 fallback
  - 再由异步 AI 补 pending / provisional / conflict / summary

### 5.6 字段级仲裁（新增硬规范）

统一理解输出不是最终真值，正式写库前必须经过字段级仲裁。

仲裁优先级固定为：

1. 原文显性硬证据
2. 系统可验证派生值
3. AI 结构化值
4. 弱推断值

字段分层：

- 硬证据字段：
  - `sex`
  - `age_label`
  - `age`
  - `phone`
  - `wechat`
  - `location`
  - `education`
  - `occupation`
  - `marital_status`
  - 显性 `monthly_income`
- 半结构化偏好字段：
  - `partner_gender_preference`
  - `partner_pref_*`
  - `partner_requirement`
- 软画像字段：
  - `soft_profile_summary`
  - `partner_summary`

硬规则：

1. 只要当前轮已经提取到明确 `age_label/birth_year`，则 `age` 必须由系统派生；AI 给出的冲突年龄不得直接 committed
2. 联系方式必须服从原文类型证据
   - `微信联系我 xxx` 不得自动扩写成 `phone + wechat`
   - `电话 xxx` 不得自动改写为 `wechat`
3. AI 成功并不意味着 fallback/证据层失效；证据层必须继续参与仲裁
4. 无法验证且与显性证据冲突的 AI 值，必须进入 `rejected` 或 `pending_confirm`
5. `partner_requirement` 与本人信息、兴趣、自我标签必须严格分流，禁止串槽

目标：

- AI 负责理解复杂语义
- 证据层负责守住硬真值
- 仲裁层负责输出可写真值
- 下游不再自行决定“到底该信谁”

---

## 6. 字段状态机（新增硬规范）

状态集合：

- `rejected`
- `pending_confirm`
- `provisional`
- `committed`

状态转移：

- `rejected -> pending_confirm -> provisional -> committed`

禁止：

- `committed` 被低状态反向覆盖
- fallback 结果直接把高风险字段写成 `committed`

---

## 7. 冲突与覆盖规则（新增硬规范）

1. `committed` 不得被 `provisional/pending_confirm` 覆盖
2. 高风险字段冲突默认进入 `pending_confirm`
3. 仅在显式纠正语义（如 `correct_profile`）或高置信确认下允许替换稳定字段
4. compat 投影层禁止反向写回语义主链
5. 预生成补识别、上下文补槽、派生字段不得把 `accepted_fields` 从无变有，不得直接构造 committed 主档写入

---

## 8. 写库并发保护（CAS 规范）

`TurnPersistencePlan` 需携带：

- `expected_profile_updated_at`
- `field_version`

写库执行前必须校验：

- 当前 profile 版本与 `expected_profile_updated_at` 一致才允许批量提交
- 不一致则触发 guard，回退到确认/重算流程，不得盲写

---

## 9. 模块职责（最终版）

落点仍集中在：

- `src/modules/conversation_understanding/domain/`

主入口：

- `UnifiedTurnUnderstandingService.analyze(...)`

配套优先级策略规范：

- `docs/09_TURN_PRIORITY_POLICY_DESIGN.md`

关键模块职责：

- `ai_semantic_extraction_service.py`
  - AI 结构化提取
  - 严格 JSON 协议
  - 超时预算与降级
- `field_acceptance_service.py`
  - 校验
  - committed/provisional/pending/rejected 分流
  - AI `direct_write` 提交契约
  - 高风险字段非 AI 提交门控
- `field_update_policy_service.py`
  - 与历史 profile 冲突策略
  - 状态提升与降级规则
  - field_version 计算
- `persistence_plan_service.py`
  - 生成唯一正式写库计划
  - 包含 provisional/pending 与 expected_profile_updated_at
- `chat_service_collection_extraction_service.py`
  - 直接消费 `persistence_plan.accepted_fields`
  - 执行最小格式归一化与主档写入
  - 禁止回退到旧 extraction 重新判定 self/partner 语义

下游依赖方向：

- `ChatService -> UnifiedTurnUnderstandingService`
- `Collection -> TurnPersistencePlan`
- `Response -> semantic_frame + persistence_plan`
- `Display -> profile + plan projection`

禁止调用路径：

1. `ChatService -> user_message -> new field inference`
2. `Postprocess -> raw user_message -> partner_requirement recompose`
3. `Persistence -> raw user_message -> derive self field`
4. `pre_generation_resolution -> persistence_plan.accepted_fields += committed field`

---

## 10. “先回复后理解”规范化

允许先回复，但必须满足：

1. 仅在状态机安全栅栏内执行
2. 未确认字段不得入正式档案
3. 不得改写已 committed 的核心字段

这是一种可控能力，不是退化行为。

---

## 11. 时延与稳定性策略（新增硬规范）

1. 同步主链路先做切块 + 高置信 deterministic 提取，再按场景启用 AI 语义增强
2. 同步 AI 的职责是提高精度，不再承担“主链唯一理解器”角色
3. 非高价值轮次默认走同步轻链 + 异步 backfill，避免全量每轮都打 AI
4. 同步 AI 超时后必须立刻降级到阶段 A 可用输出，且该输出必须包含块级抽取结果与摘要，不得退化成“没听懂”
5. 异步 backfill 调度必须做到“全入口统一评估”，但不是“全量每轮都打 AI”
6. 异步 backfill 不再采用 `already_ai -> 一刀切跳过`
7. 只有当主链没有 `pending/provisional/conflict/missing_summary` 时，才允许 `already_ai` 直接 skip
8. 异步 backfill 一旦触发，任务必须缩窄为“定向补洞”，优先补：
   - `pending_fields`
   - `provisional_fields`
   - 冲突字段
   - `soft_profile_summary`
   - `partner_summary`
9. 异步 backfill 任务必须做 account 级并发去重，避免同账号重复堆积
10. 异步 backfill 任务必须做 message fingerprint 去重，避免同一句高价值输入被重复补写
11. 异步 backfill 连续失败或 `ai_not_ready` 后必须进入 cooldown，避免高价值轮次反复打空枪
12. 异步补全不阻塞当前回复
13. 生产环境下 dense intro 同步 AI 预算应保持短预算，默认目标 `8~12s`；更长超时只用于排障验证，不应作为常态主链配置

### 11.1 AI 提交契约

统一口径：

1. AI 负责回答“这句话在说什么”
2. `write_mode=direct_write` 表示 AI 认为字段归属、字段值、字段 owner 已明确
3. 一旦 `direct_write` 进入 `accepted(committed)`，下游必须直接入库
4. 下游不得再因为旧 extraction 规则、上下文补识别、影子 guard 把它改成别的字段或直接丢弃

只有以下情况允许不入主档：

1. `write_mode=soft_confirm`
2. 字段格式非法
3. 覆盖稳定旧值且没有纠正语义
4. CAS guard 失败

### 11.2 全入口统一 async backfill 调度

统一原则：

1. 每个主响应出口都必须进入同一套 async backfill decision policy
2. policy 先判断“值不值得补”，运行时门控再判断“现在能不能补”
3. 同步主链不等待 async backfill 结果，所有补写都在回复后异步完成

当前必须覆盖的主出口：

- `model`
- `quick_faq`
- `preset_response`
- `pre_generation_short_circuit`

说明：

- `already_ended` 等无统一理解结果的超早返回路径，也要进入统一调度入口，但会因 `missing_understanding` 被明确跳过
- 不允许再出现“只有 model 路径会评估 backfill，其他路由直接绕过”的实现

### 11.3 高价值触发策略（不是每轮都打 AI）

只有命中高价值条件的轮次才允许真正触发异步 AI 语义补全。

必须触发的典型场景：

1. 存在 `provisional_fields` 或 `pending_fields`
2. 命中高风险字段：`occupation, age, monthly_income, contact, partner_requirement, sex`
3. 混合轮次：同一句同时包含 FAQ + profile / contact / preference
4. 多槽位长句：同轮出现多个有效字段，尤其是 opening 自我介绍型输入
5. `correction` / 冲突修正 / 纠偏轮次
6. partner requirement 结构化程度不足，仍需要 AI 做补全或重判

默认跳过场景：

1. 纯 FAQ，且没有新字段进入计划
2. 纯确认 / 纯寒暄 / 纯结束语
3. 无新增信息、无高风险字段、无 provisional/pending 的低价值轮次

### 11.4 调度门控与去重

调度顺序固定为：

1. `policy_decision`
2. env 开关
3. account inflight 去重
4. cooldown 检查
5. fingerprint 去重
6. 真正创建异步任务

要求：

1. `policy_decision` 必须输出：`should_schedule / reason / route / target_fields / fingerprint`
2. fingerprint 不能只看原文文本，至少要纳入 `route + normalized_message + target_fields`
3. cooldown 必须是 account 级，防止单账号在 AI 超时期间持续打满异步任务
4. `skip reason` 必须可观测，不能只记“没触发”

### 11.5 最终回复生成链路解耦（新增硬规范）

1. 最终回复模型只负责生成用户可见文案，不再承担字段抽取职责
2. 最终回复 prompt 禁止再拼接 `<extract>` 或其他结构化抽取协议
3. 开场意图判断不再由最终回复模型二次输出 `<opening_intent>`；开场/语义解释权只保留在统一理解域
4. 字段写库只消费 `semantic_frame + persistence_plan`，不得再依赖最终回复文本中的结构化块
5. FAQ / 确定性答疑 / 联系方式记录类轮次，若优先级层已判定 `user_question`，优先走 `quick_faq` 或确定性直返，不得因为“同句含资料/联系方式”被无条件推回慢模型
6. 最终回复模型默认采用面向短答复的 provider 预算：
   - 优先使用 `max_completion_tokens`
   - 显式下调 reasoning 强度（默认 `minimal`）
   - 若 provider 不支持高级参数，允许自动兼容回退，但必须打日志
7. 目标是把“可见回复生成”从多任务重载链路收口为单任务短链路，避免再出现 `max_tokens=360` 但 `completion_tokens` 异常膨胀的问题

### 11.6 与 `11_AI_RESPONSE_UNIFIED_GENERATION_DESIGN.md` 的职责边界（本次新增）

统一理解域和统一生成域必须严格解耦，边界如下：

1. 统一理解域负责解释原文、产出 `semantic_frame / persistence_plan / priority_decision`
2. 统一生成域负责基于这些结构化结果生成当前轮用户可见正文
3. async backfill 可以补语义、提状态、升降字段状态，但不能改当前轮已经冻结的 `display_response`
4. 如果 backfill 在当前轮回复后成功完成，它影响的是：
   - 后续 profile
   - 后续 turn decision
   - 下一轮上下文
   而不是当前轮用户已经看到的文案
5. 任何“因为理解结果更完整了，所以想改一下当前轮文案”的需求，都必须发生在 `response_draft_service` 之前；delivery freeze 之后一律禁止

这条边界的目的只有一个：

- 统一理解继续提高字段质量
- 统一生成继续保证真人感输出
- 两者都不能通过“生成后再改正文”来相互补锅

### 11.7 提交字段单一真相（避免“像没记忆”）

为消除“本轮识别正确但下一轮决策看不到”的断裂，必须收口为单一提交视图：

1. 决策影子画像、提取合并、生成追问、落库都统一消费 `accepted_fields(committed)`。
2. 高风险字段放行判断只能走统一函数（例如 `explicit_self_marker` 放行），禁止各模块各写一套条件。
3. 任何模块禁止再写“source_channel 不是 ai 就一刀切跳过”的私有分支。
4. 验收标准：用户已明确回答的字段（如职业）在同轮后续决策中必须可见，不能再重复追问同字段。

---

## 12. SLO 与观测指标（新增）

必须持续观测：

- `ai_timeout_rate`
- `provisional_to_committed_rate`
- `pending_confirm_rate`
- `dirty_write_rate`
- `async_backfill_evaluated`
- `async_backfill_scheduled`
- `async_backfill_skip_rate`
- `async_backfill_success_rate`
- `async_backfill_latency_ms_p95`
- `async_backfill_route_coverage`
- `async_backfill_target_field_distribution`
- `reply_generation_latency_ms_p95`
- `completion_token_inflation_ratio`
- `generation_reasoning_tokens_p95`

验收阈值：

1. 高风险字段脏写率：`0`
2. AI 成功后二次解释原文次数：`0`
3. 噪声 occupation 写入（如“怎么多了”“女生找男朋友”）：`0`
4. 关键回放样本无回归，长期稳定通过

---

## 13. 样本验收（必须持续回放）

样本 1：

`找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就 怎么多了`

必须满足：

- `occupation = 空`
- `partner_pref_age != 年龄18左右`
- `monthly_income` 与 `partner_pref_height/partner_pref_age` 正确分离
- `一年18左右` 不得因为口语化表达而直接丢失
- 尾部噪声短语如 `暂时就 怎么多了` 不得污染 `occupation / partner_requirement`

样本 2：

`可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下`

必须满足：

- self / partner / contact / faq 多域并存时不串槽
- 联系方式与 FAQ 语义保留，不污染 self 字段

---

## 14. 实施顺序（质量优先）

1. 长句切块 + 块分类 + 显性 `no_reask_fields`
2. 硬字段 / 软画像 / 择偶摘要分流
3. 字段状态机 + 高风险硬门控 + 写库入口只吃 committed
4. 同步 AI 降级为增强器，异步 backfill 负责补细节和状态提升
5. 冲突策略 + CAS 版本保护
6. 清理所有 legacy 原文解释路径
7. 全量回归 + 灰度 + 指标验收达标后全量切换

---

## 15. 最终架构结论

最终决策不变，但执行标准升级：

- `TurnSemanticFrame` 是唯一语义真源
- `TurnPersistencePlan` 是唯一正式写库计划
- `resolved_slots` 是 compat 投影，不得反向主导语义
- 统一理解域收回解释权，同时引入状态机、CAS 和 SLO，确保“质量优先”可工程化落地
- 当前阶段允许新旧实现并存，但正式主链只能有一个脑子：`UnifiedTurnUnderstandingService`
