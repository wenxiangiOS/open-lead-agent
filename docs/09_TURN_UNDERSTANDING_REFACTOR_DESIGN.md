# 09 单轮理解统一重构方案

## 目标

在不降低拟人化、不降低 AI 理解能力、不把对话做成模板机的前提下，统一“这一轮发生了什么”的判断口径，解决：

- 字段漏收
- 复合回答漏拆
- FAQ / 主线 / 联系方式切换打架
- 联系方式完成与收尾混淆
- 生成后 guard 过重导致自然回复被洗坏

## 总原则

- 规则决定做什么
- AI 决定怎么说

因此：

- 统一理解和决策
- 不统一表达内容
- 不写死固定承接句
- 不让 Output Guard 整句重写

## 最终分层

主链路统一为：

1. `Context Loader`
2. `Turn Understanding`
3. `Policy Decision`
4. `Response Generation`
5. `Minimal Output Guard`

其中真正新增的核心模块只有：

- `turn_understanding_service`

## 模块边界

各层职责严格固定：

- `Context Loader`：读取 `message_count / last_response / user_profile / contact_context / pending_confirmation`
- `Turn Understanding`：产出单轮结构化理解结果
- `Policy Decision`：决定本轮允许动作和推进边界
- `Response Generation`：让 AI 自然生成回复
- `Minimal Output Guard`：只做最小纠偏

明确禁止：

- `Turn Understanding` 返回固定回复文案
- `Policy Decision` 返回固定问句模板
- `Output Guard` 大面积改写模型输出
- `ChatService` 再新增第二套理解逻辑

## 代码接入点

当前项目里的核心接入关系应保持为：

- `src/modules/conversation/application/process_chat_turn.py`
  - 负责拉取上下文并触发主流程
- `src/modules/conversation/domain/turn_understanding_service.py`
  - 负责单轮理解
- `src/modules/conversation/domain/turn_understanding_models.py`
  - 负责理解结果 schema
- `src/modules/profile_collection/domain/profile_collection_policy.py`
  - 负责动作边界与字段推进策略
- `src/services/core/chat_service.py`
  - 负责编排、状态副作用和兼容入口

这意味着后续新增规则时，优先级应该是：

1. 单轮输入理解规则放到 `turn_understanding_service`
2. 动作约束和推进规则放到 `profile_collection_policy`
3. 只有跨服务编排和状态副作用，才放到 `ChatService`

## 一级输入场景

统一收成 10 类：

1. `opening`
2. `faq_concern`
3. `profile_answer`
4. `contact_answer`
5. `confirmation`
6. `refusal_boundary_complaint`
7. `correction`
8. `invalid_input`
9. `closing_exit`
10. `risk_guard`

说明：

- 这 10 类只负责回答“这轮是什么性质”
- 不直接绑定固定模板回复
- 不直接决定具体问句

## 二级 signals

以下内容保留为 `subtype` / `secondary_signals`，不升为一级输入场景：

- `proactive_profile_provide`
- `proactive_contact_provide`
- `multi_slot_compound`
- `active_revise`
- `contact_refusal`
- `boundary_defensive`
- `complaint`
- `weak_confirmation`
- `low_cooperation_short_answer`
- `ambiguous_short_answer`
- `pending_confirmation_reply`
- `faq_just_resolved`

## 哪些不属于输入场景

以下内容不纳入一级输入分类：

- `恢复主线`
- `联系方式完成后的后处理`

它们属于流程决策层，应在 understanding 后作为结构化提示继续传递：

- `answer_first`
- `resume_hint`
- `resume_target`
- `contact_complete`
- `allow_end_conversation`
- `should_end_conversation`

## turn_understanding_service 职责

该模块只负责：

1. 一级输入场景识别
2. 二级 signals 识别
3. `slot_candidates`
4. `resolved_slots`
5. `blocked_slots`
6. `answer_first`
7. `resume_hint`

不负责：

- 最终回复文案
- 联系方式状态机
- 收尾判断
- 落库
- prompt 话术模板

## 统一输出对象

建议统一输出如下对象：

```json
{
  "primary_turn_type": "profile_answer",
  "subtype": "multi_slot_compound",
  "secondary_signals": ["proactive_profile_provide"],
  "risk_flags": [],
  "slot_candidates": {
    "sex": {"value": "男", "confidence": 0.95, "source": "rule"},
    "marital_status": {"value": "单身", "confidence": 0.93, "source": "rule"}
  },
  "resolved_slots": {
    "sex": "男",
    "marital_status": "单身"
  },
  "blocked_slots": {},
  "answer_first": false,
  "resume_hint": null,
  "context_ack_type": "profile_ack"
}
```

## 建议 schema

建议长期稳定维护以下结构：

```python
TurnUnderstandingResult(
    primary_turn_type: str,
    subtype: str | None,
    secondary_signals: list[str],
    risk_flags: list[str],
    slot_candidates: dict[str, SlotCandidate],
    resolved_slots: dict[str, str],
    blocked_slots: dict[str, BlockedSlot],
    answer_first: bool,
    resume_hint: str | None,
    context_ack_type: str | None,
    context_ack_payload: dict[str, str],
    complaint_reason: str | None,
    resume_profile_collection: bool,
    post_answer_reentry: bool,
    confidence: float,
    notes: list[str],
)
```

关键要求：

- `slot_candidates` 保留“识别到但未必接收”的原始能力
- `resolved_slots` 只保留允许进入后续流程的结果
- `blocked_slots` 必须能解释为什么被拦
- `context_ack_payload` 只提供轻量承接素材，不提供整句文案

## slot resolve 规则

必须统一成三层：

1. `slot_candidates`
2. `resolved_slots`
3. `blocked_slots`

核心要求：

- 复合短答必须能统一拆解
- 被识别但不能接收的字段必须明确 block reason
- 不允许直接从“识别到”跳“落库”

必须优先解决这些问题：

- `男，单身` -> `sex + marital_status`
- `我今年36` -> `age`
- `本科，160以上` -> `education + partner_requirement`
- `找男生` 不得污染 `sex`
- `本科` 不得污染 `partner_requirement`
- `电话不方便，微信可以` 要拆成拒绝电话 + 微信偏好

## Policy 输出约束

建议长期稳定输出以下类型字段：

- `action`
- `primary_move`
- `main_target`
- `side_target`
- `allow_contact_transition`
- `allow_end_conversation`
- `require_soft_confirmation`
- `resume_target`
- `resume_mode`
- `prioritize_user_question`

其中：

- `action` / `primary_move` 决定本轮执行类型
- `main_target` / `side_target` 决定问什么
- `resume_target` / `resume_mode` 决定 FAQ 或 complaint 后怎么回主线
- `allow_contact_transition` / `allow_end_conversation` 决定流程边界

不允许把这些字段退化成固定文案。

## Policy 只做动作决策

Policy 层只负责输出：

- `action`
- `main_target`
- `side_target`
- `allow_contact_transition`
- `allow_end_conversation`
- `require_soft_confirmation`

不输出：

- 固定问句
- 固定承接句

## Generation 保持自由表达

Generation 继续由 AI 主导：

- 怎么承接
- 怎么组织顺序
- 语气轻重
- 是否自然接一句

结构层只提供：

- 这轮先答还是先问
- 主字段是什么
- 顺带字段是什么
- 是否允许切联系方式
- 是否允许收尾

## Output Guard 最小化

最终只保留最小纠偏：

- 错误字段拦截
- 错误收尾拦截
- 错误承诺拦截
- 明显误判话术拦截
- 合规边界拦截

明确禁止：

- 整句覆盖
- 模板替换
- 大面积文案重写

建议 guard 长期只保留这几类：

1. 已成功提取字段后，禁止“看不懂 / 打错字”类错误回复
2. `contact_complete=false` 时，禁止承诺“后续联系你”
3. `closing_exit` 时，禁止继续追字段
4. `risk_guard` 时，禁止恢复普通主线
5. 已拒留电话或微信时，禁止继续硬推同一联系方式

## 联系方式与收尾

联系方式和收尾继续保持独立域：

- `ContactCollectionService`
- `ConversationEndingService`

统一口径：

- `contact_complete != should_end_conversation`

有联系方式时：

- 联系方式流程完成
- 主线资料完成 / 问尽
- 当前轮允许结束

三者同时满足，才可正常收尾。

无联系方式时：

- 可以结束
- 但不能承诺“会联系你 / 等通知”

## 关键交互样例

这些样例应该长期作为方案验收基线：

- `男，单身`
  - `primary_turn_type=profile_answer`
  - `resolved_slots={sex, marital_status}`
- `我今年36`
  - `resolved_slots={age}`
  - 生成后不得出现“打错字”
- `本科`
  - `resolved_slots={education}`
  - `blocked_slots.partner_requirement` 应记录污染拦截
- `我在广州，你们多久联系我`
  - `primary_turn_type=faq_concern`
  - `resolved_slots={location}`
  - `answer_first=true`
  - `resume_hint=profile_mainline`
- `电话不方便，微信可以`
  - `primary_turn_type=contact_answer`
  - 应命中联系方式拒绝 + 偏好切换
- `先这样吧`
  - `primary_turn_type=closing_exit`
  - 不允许继续追字段

## 工程要求

1. `turn_understanding_service` 不得返回固定回复文本
2. `policy` 不得返回固定问句
3. `output_guard` 不得整句重写
4. 所有回归验收必须同时看：
   - 字段正确率
   - 流程正确率
   - 拟人化 / 自然度

## 落地顺序

1. 定义 schema
2. 接入 `turn_understanding_service`
3. 统一一级场景与二级 signals
4. 用 understanding 结果参与字段融合
5. 让 Policy 消费 understanding 结果
6. 缩减生成后重 guard

## 测试与验收

建议长期保留以下测试分层：

### 1. understanding 单测

覆盖：

- 10 类一级输入场景
- 核心二级 signals
- 复合回答拆槽
- `blocked_slots` 原因
- FAQ 混资料
- contact preference switch

### 2. policy 单测

覆盖：

- `main_target / side_target`
- `allow_contact_transition`
- `allow_end_conversation`
- `resume_target / resume_mode`
- `prioritize_user_question`

### 3. chat_service 回归

覆盖：

- FAQ / 主线 / complaint / boundary 切换
- opening fallback
- profile bridge
- contact / ending 联动
- tone guard 不洗坏自然回复

### 4. 质量门禁

每次大改后至少人工抽查：

- 有没有模板腔
- 有没有明显机器人感
- 有没有把正常回复洗坏
- 有没有因为规则收口导致对话变笨

## 实施清单

建议按阶段推进，每个阶段都必须可单独回归、可单独回滚。

### Phase 1: 协议固化

- 定义 `TurnUnderstandingResult` schema
- 固定 10 类一级输入场景
- 固定二级 signals 命名
- 固定 `slot_candidates / resolved_slots / blocked_slots` 语义
- 补 understanding 基础单测

完成标准：

- 单轮理解输出结构稳定
- 关键 case 可直接通过 schema 验证
- 不依赖生成层才能判断是否正确

### Phase 2: 理解层接管

- opening / faq / complaint / boundary / withdraw / risk 统一进入 understanding
- contact candidate 提取进入 understanding
- deterministic slot extraction 进入 understanding
- extraction guards 进入 understanding
- `context_ack_type / context_ack_payload` 进入 understanding

完成标准：

- `ChatService` 不再保留第二套真实理解逻辑
- 旧 helper 最多保留兼容壳
- understanding 成为唯一理解实现源

### Phase 3: Policy 收口

- `profile_collection_policy` 消费 understanding 结果
- 输出 `primary_move / main_target / side_target / resume_target`
- FAQ / complaint / boundary / closing 场景都通过 policy 派生动作
- 减少 `ChatService` 里的行为覆盖逻辑

完成标准：

- 动作边界不再散落在多层 if/else
- `Policy` 成为唯一动作派生入口
- `ChatService` 只做编排和状态副作用

### Phase 4: 生成链对齐

- prompt 只消费 understanding + policy 的结构化结果
- 删除固定问句倾向
- 删除结构层对具体话术的控制
- 保留 AI 自然承接和追问自由度

完成标准：

- 回复未出现明显模板化
- FAQ 回主线、短答承接、多槽位承接仍自然
- 不因规则收口导致对话变硬

### Phase 5: Guard 收缩

- 只保留最小错误拦截
- 删除整句覆盖型后处理
- 删除用 guard 代替 policy 的推进逻辑
- 删除与 understanding 重复的行为修补

完成标准：

- guard 只剩安全和明显错误兜底
- 自然回复不再被大面积洗坏
- 仍能拦住错误收尾、错误承诺、明显误判

## 回滚策略

每个阶段都应保留独立回滚点：

- schema 变更只影响 understanding 输出，不直接影响落库
- policy 接管前，旧 decision 分支可保留一版兼容路径
- guard 收缩应按规则逐条下线，而不是一次删空
- 生成链改动必须先通过 regression，再扩大覆盖

如果回归出现以下问题，应优先局部回滚最近阶段：

- FAQ 无法正确优先
- 资料字段开始明显漏收
- 联系方式 / 收尾逻辑异常
- 对话突然出现模板腔
- 短答承接明显变硬

## 发布前检查

每次准备上线前，至少检查以下项目：

- `turn_understanding_service` 是否新增了固定文案
- `policy` 是否新增了固定问句
- `ChatService` 是否重新长出新的意图判断分支
- `Output Guard` 是否新增整句覆盖
- FAQ / opening / boundary / correction / contact / closing 的关键回归是否全绿

## Review 清单

代码 review 时，优先看这些问题：

1. 这段新规则到底属于 understanding、policy，还是只是状态编排
2. 是否把“判断”偷偷写进了生成提示词
3. 是否出现了新的平行判断链
4. 是否把自然承接写成了固定模板
5. 是否增加了会洗坏回复的 guard
6. 是否补了对应单测和回归

## 常见反模式

以下写法在这套架构里应当直接避免：

- 在 `ChatService` 里新增 `if "怎么收费" in message` 之类的意图判断
- 在 policy 里直接拼问句
- 在 understanding 里返回整句回复
- 在 guard 里整段替换模型输出
- 为了修一个 case，新增第三套“快速判断” helper
- 把 `嗯 / 还行 / 一般吧` 一律按无效输入处理

## 长期维护建议

后续继续演进时，建议保持以下顺序：

1. 先补失败样例
2. 再决定是 understanding 问题、policy 问题还是 guard 问题
3. 只在对应层修，不跨层乱补
4. 修完必须跑 understanding 单测和 chat_service 回归

如果一个问题需要同时改 understanding、policy、guard，优先怀疑边界又开始混了。

## 项目任务拆解表

下面这份拆解表按“阶段 -> 文件 -> 任务 -> 验收”组织，适合直接拿去排期或建任务卡。

### Task Group A: Understanding 协议与模型

涉及文件：

- `src/modules/conversation/domain/turn_understanding_models.py`
- `tests/unit/test_turn_understanding_service.py`

任务：

- 固化 `TurnUnderstandingResult` 字段语义
- 固化 10 类一级输入场景枚举
- 固化二级 `subtype / secondary_signals` 命名
- 固化 `SlotCandidate / BlockedSlot` 结构
- 补 schema 级单测

验收：

- schema 字段无歧义
- understanding 单测可直接断言 `primary_turn_type / resolved_slots / blocked_slots`
- 新增 case 时无需依赖生成层判断正误

### Task Group B: Understanding 主逻辑

涉及文件：

- `src/modules/conversation/domain/turn_understanding_service.py`
- `tests/unit/test_turn_understanding_service.py`

任务：

- 统一 opening / faq / profile / contact / confirmation / correction / closing / risk 识别
- 统一 `context_ack_type / context_ack_payload`
- 统一 `complaint_reason / resume_profile_collection / post_answer_reentry`
- 统一 `slot_candidates / resolved_slots / blocked_slots`
- 统一 deterministic extraction 与 extraction guards

验收：

- `turn_understanding_service` 成为唯一理解实现源
- 不再存在第二套平行单轮理解逻辑
- 关键样例全部覆盖单测

### Task Group C: Policy 收口

涉及文件：

- `src/modules/profile_collection/domain/profile_collection_policy.py`
- `src/modules/profile_collection/application/profile_collection_coordinator.py`
- `tests/unit/test_chat_service_regressions.py`

任务：

- 让 policy 以 understanding 结果为核心输入
- 输出 `action / primary_move / main_target / side_target / resume_target / resume_mode`
- 统一 FAQ 优先、complaint repair、resume mainline、contact transition、ending boundary
- 删除 policy 之外的重复动作派生

验收：

- 主动作边界不再散落在 `ChatService` 各处
- FAQ / complaint / boundary / closing 的动作派生稳定
- 不出现 policy 和 understanding 打架

### Task Group D: ChatService 编排收薄

涉及文件：

- `src/services/core/chat_service.py`
- `src/modules/conversation/application/process_chat_turn.py`
- `tests/unit/test_chat_service_regressions.py`
- `tests/unit/test_process_chat_turn_use_case.py`

任务：

- 让 `ChatService` 只负责 orchestration、状态副作用、兼容入口
- 把理解型 helper 降成兼容壳或删除
- 把 general path 的默认派生集中成 helper
- 把 quick decision / opening fallback / contact-context FAQ 特例集中收口

验收：

- `ChatService` 不再是第二个理解中心
- `_build_turn_decision` 维持 orchestration 角色
- 回归通过且不降低自然度

### Task Group E: Generation 与 Guard 对齐

涉及文件：

- `src/services/prompts/prompts.py`
- `src/services/core/chat_service.py`
- 相关 guard / prompt 组装文件
- `tests/unit/test_chat_service_regressions.py`

任务：

- prompt 只消费 understanding + policy 的结构化结果
- 保留自然承接，不新增固定问句
- 删除整句覆盖式 guard
- 保留最小错误拦截

验收：

- 没有明显模板腔
- FAQ 后回主线自然
- 短答承接自然
- guard 不再大面积洗坏回复

### Task Group F: Contact / Ending 边界校正

涉及文件：

- `src/services/collection/contact_collection_service.py`
- `src/modules/conversation/domain/conversation_ending_service.py`
- `src/services/core/chat_service.py`
- `tests/unit/test_chat_service_regressions.py`

任务：

- 固化 `contact_complete != should_end_conversation`
- 区分“联系方式完成”和“允许结束”
- 无联系方式收尾时禁止联系承诺
- 有联系方式但主线未完成时优先 resume profile

验收：

- contact complete 和 ending 不再混淆
- 无联系方式结束时不会乱承诺
- profile 未完成时不会提前收尾

## 建议任务顺序

如果按最稳的工程顺序推进，建议是：

1. Task Group A
2. Task Group B
3. Task Group C
4. Task Group D
5. Task Group E
6. Task Group F

其中：

- A/B 是“统一理解”
- C/D 是“收口动作和编排”
- E/F 是“保质上线”

## 每阶段完成定义

每个 Task Group 完成，都至少满足：

1. 有对应代码变更
2. 有对应测试补充或回归验证
3. 没有引入新的模板化表达
4. 没有把理解逻辑重新塞回 `ChatService`
5. 文档与实现保持一致

## 文件级 TODO Checklist

下面这份 checklist 不是“现在必须改完”，而是后续维护时的文件级约束和待办清单。

### `src/modules/conversation/domain/turn_understanding_models.py`

保留职责：

- 定义 `TurnUnderstandingResult`
- 定义 `SlotCandidate / BlockedSlot`
- 固化 understanding 输出语义

后续待办：

- 如新增字段，先补字段语义说明
- 如新增 `subtype / signal`，先保证命名与现有风格一致
- 避免在 model 层塞业务逻辑

禁止事项：

- 不在 model 层拼接默认文案
- 不把 policy 字段塞回 understanding model

### `src/modules/conversation/domain/turn_understanding_service.py`

保留职责：

- 单轮输入识别
- slot resolve
- extraction guards
- context ack payload 生成
- FAQ / opening / complaint / boundary / closing / risk 判断

后续待办：

- 新增单轮理解规则优先放这里
- 新增 `blocked_slots` 原因时补单测
- 定期清理仅为兼容历史遗留 case 的规则

禁止事项：

- 不返回整句回复
- 不拼固定问句
- 不把联系方式状态机和 ending 规则卷进来

### `src/modules/profile_collection/domain/profile_collection_policy.py`

保留职责：

- 动作边界
- main / side target 派生
- resume target / mode 派生
- FAQ / complaint / closing / contact transition 的策略约束

后续待办：

- 新增动作边界优先放这里
- 减少对 message 文本的直接依赖，优先消费 understanding 结果
- 补 policy 单测而不是只靠 chat_service 回归

禁止事项：

- 不直接写固定话术
- 不重复做一遍 turn understanding

### `src/modules/conversation/application/process_chat_turn.py`

保留职责：

- 拉取上下文
- 调用 understanding / policy / generation / guard
- 处理主流程编排

后续待办：

- 保持 orchestration 简洁
- 新增链路节点时先确认是不是应该下沉到 domain service

禁止事项：

- 不直接新增用户意图判断
- 不在 use case 层塞规则词库

### `src/services/core/chat_service.py`

保留职责：

- 编排
- 状态副作用
- 历史兼容入口
- prompt / guard / contact / ending 的主链连接

后续待办：

- 持续清理已经退化为兼容壳的 helper
- 优先把“理解型”逻辑再往 understanding / policy 挪
- 保持 `_build_turn_decision` 只做 orchestration
- 对兼容壳按“无调用点 -> 仅内部调用 -> 测试直接依赖”分层清理

禁止事项：

- 不再新增第二套单轮理解逻辑
- 不在这里补“临时 if”修 FAQ / complaint / opening 判定
- 不把自然表达模板化

### `src/services/prompts/prompts.py`

保留职责：

- prompt 文本组织
- 风格与禁止项约束

后续待办：

- prompt 只消费结构化结果，不消费第二套隐式判断
- 保持对自然承接的引导，而不是模板控制

禁止事项：

- 不在 prompt 里重复写一套 turn classification
- 不把 `main_target` 写死成固定问句

### `src/services/collection/contact_collection_service.py`

保留职责：

- 联系方式状态机
- 电话 / 微信收集与拒绝处理

后续待办：

- 继续只消费 `contact_answer / contact_refusal / preference_switch` 这类明确结构信号
- 保持与 ending 解耦

禁止事项：

- 不从联系方式状态反向承担 turn understanding
- 不自行决定 FAQ / profile / closing 分类

### `src/modules/conversation/domain/conversation_ending_service.py`

保留职责：

- 收尾条件判断
- ending response 选择

后续待办：

- 继续固化 `contact_complete != should_end_conversation`
- 单独维护“无联系方式结束不可承诺联系”的规则

禁止事项：

- 不把联系方式完成直接等同于可以收尾
- 不回头接管 profile mainline 推进

### `tests/unit/test_turn_understanding_service.py`

保留职责：

- 单轮理解核心测试

后续待办：

- 新增理解规则必须补这里
- 新增 blocked reason 必须补这里
- 混合输入场景优先补这里

禁止事项：

- 不把跨层编排结果断言塞进这里
- 不把 contact / ending / prompt 联动回归塞进这里

### `tests/unit/test_chat_service_text_helpers.py`

保留职责：

- 纯文本 helper / 纯格式清洗测试
- 不依赖主链编排和状态副作用的静态或轻实例方法

后续待办：

- 继续把 `sanitize_robotic_tone / collapse_duplicate_ack_segments / clean_response` 这类纯文本规则迁到这里
- `format_fast_path_ack(...)` 这类轻实例文本 helper 也优先收敛到这里
- 保持和 `test_chat_service_regressions.py` 边界清晰

禁止事项：

- 不把依赖实例初始化或跨层状态的 helper 硬迁到这里
- 不在这里测 policy、contact、ending 联动

### `tests/unit/test_chat_service_opening_helpers.py`

保留职责：

- opening intent 纯解析 / 纯规则 helper 测试
- 不依赖主链状态推进的 opening consistency 辅助逻辑

后续待办：

- 把更多 opening block / priority / consistency 纯规则测试继续收敛到这里

禁止事项：

- 不在这里测试 opening fallback 的整条主链行为
- 不把依赖 turn decision 全流程编排的 case 迁到这里

### `tests/unit/test_chat_service_bridge_helpers.py`

保留职责：

- `ChatService` 中与 bridge-back 前缀、桥接标记相关的纯规则 helper 测试
- 不依赖主链编排、副作用或 AI 生成的 bridge 规则验证

后续待办：

- 继续把 `_build_bridge_back_prefix(...)` 及同层纯桥接 helper 的窄测试收敛到这里
- 保持与 `test_chat_service_regressions.py` 的跨层联动边界清晰

禁止事项：

- 不在这里测试 FAQ/complaint/boundary 的整条恢复主线链路
- 不把依赖 policy、ending、contact 联动的断言迁到这里

### `tests/unit/test_chat_service_summary_helpers.py`

保留职责：

- `ChatService` 中低频画像小结相关的纯 helper 测试
- 例如 `_should_emit_profile_summary(...)` 与 `_build_profile_summary_line(...)` 的表达规则

后续待办：

- 继续把低频画像小结的纯规则断言从大回归收敛到这里
- 保持与 `test_chat_service_regressions.py` 的跨层行为边界清晰

禁止事项：

- 不在这里测试真实主回复注入、AI 生成或 ending/contact 联动
- 不把依赖主链状态推进的断言迁到这里

### `tests/unit/test_chat_service_followup_helpers.py`

保留职责：

- `ChatService` 中交错追问、短答续问、ack 过渡相关的纯 helper 测试
- 例如 `_build_interleaving_followup(...)`、`_ensure_short_answer_ack_transition(...)`、`_prepend_*_ack_transition(...)`

后续待办：

- 继续把纯 followup/ack helper 从大回归收敛到这里
- 保持与 `test_chat_service_regressions.py` 的跨层主链边界清晰

禁止事项：

- 不在这里测试 contact handoff、ending、policy 联动
- 不把依赖主链状态副作用的断言迁到这里

### `tests/unit/test_dialogue_manager_prompt_helpers.py`

保留职责：

- `DialogueManager` 的 prompt helper 与提示词规则测试
- 例如 `build_main_dialogue_prompt(...)` 对 `primary_move`、recent style、contact target 的提示词约束

后续待办：

- 继续把 prompt 纯规则与提示词约束从大回归收敛到这里
- 保持与 `test_process_chat_turn_use_case.py` 和 `test_chat_service_regressions.py` 的编排边界清晰

禁止事项：

- 不在这里测试真实 AI 输出、contact/ending 状态机或 use case 编排
- 不把依赖外层 orchestration 的断言迁到这里

### `tests/unit/test_dialogue_expression_helpers.py`

保留职责：

- `DialogueExpressionService` 的字段问句、桥接追问、阶段差异表达规则
- 不依赖 `ChatService` 主链、副作用和 AI 生成的表达 helper 测试

后续待办：

- 继续把 `render_field_question(...)` 的纯表达规则和桥接场景从大回归迁到这里
- `DialogueExpressionService` 的避免重复前缀、桥接差异表达等 case 也优先收敛到这里
- 补齐不同 `stage / profile / user_message` 组合下的问句选择覆盖

禁止事项：

- 不在这里测试 policy / contact / ending 联动
- 不把 `ChatService` 编排结果或 guard 组合断言迁到这里

### `tests/unit/test_chat_service_regressions.py`

保留职责：

- 历史回归保护
- 跨层联动验证

后续待办：

- 新增跨层行为回归补这里
- 每次收缩 guard 都补对应回归
- 持续把纯文本 / 纯提取 helper case 下沉到更窄的单测文件

禁止事项：

- 不把本应是 understanding 单测的 case 全堆到这里
- 不把已经适合 `test_chat_service_text_helpers.py` 的纯文本规则继续留在这里
- 不把已经适合 `test_chat_service_opening_helpers.py` 的 opening 纯规则 helper 继续留在这里
- 不把已经适合 `test_dialogue_expression_helpers.py` 的纯表达 helper 继续留在这里

### `tests/unit/test_process_chat_turn_use_case.py`

保留职责：

- 用例编排回归
- payload / final_response 一致性

后续待办：

- 新增主链分支时补 use case 级回归
- 只测编排，不在这里重复测细碎理解规则

禁止事项：

- 不把 text helper / opening helper / understanding helper 的纯规则测试挪进这里
- 不让 use case 回归承担历史兼容壳测试

## 文档维护规则

为了避免文档和实现重新脱节，后续维护时建议执行：

1. 架构边界改动，同时更新本文件
2. opening guard 改动，只更新 `08_OPENING_GUARD_DESIGN.md`
3. turn understanding / policy / guard 边界改动，更新本文件
4. 如果实现已经明显偏离文档，优先修文档或修实现，不保留“双口径”

## 兼容壳清理现状

当前 `ChatService` 里的 understanding compatibility wrappers 已基本清空，现状按三类记录如下：

### 已删除

这些 wrapper 已经没有调用点，已移除：

- `_detect_priority_question_intent`
- `_detect_followup_topic`
- `_build_context_ack_payload`
- `_extract_contact_candidate_from_message`
- `_detect_which_field_is_asked`
- `_build_lightweight_field_ack_from_message`
- `_build_opening_profile_ack_from_message`
- `_extract_deterministic_profile_fields`
- `_apply_extraction_guards`

### 暂时保留：仍有内部调用

这些方法仍被主链局部逻辑调用，短期不适合硬删，但不应继续新增规则：

- 无

### 暂时保留：测试直接依赖

以下能力目前主要在 understanding 单测中直接断言；`ChatService` 侧同名 wrapper 已不再保留：

- deterministic field extraction
- lightweight / opening ack helper
- field asked detection
- extraction guards

当前已经开始迁移的测试类型：

- `asked_field` 识别
- `opening_profile_ack`
- `lightweight_field_ack`
- 部分 deterministic extraction case
- `monthly_income` 轻提取
- 部分 extraction guards（sex context / affirmative confirmation）
- `sex_over_partner_requirement` 这类混合问句优先级 case

建议清理顺序：

1. 先删“无调用点”的死壳
2. 再把“仅内部调用”的壳收窄成更窄的 private helper
3. 最后再处理测试直接依赖的壳，并同步迁移测试到 understanding 层

补充说明：

- `_extract_deterministic_profile_fields` 和 `_apply_extraction_guards` 已从 `ChatService` 删除；主链和用例层均已直连 understanding，并在 use case 层保留最小类型兼容（如 `age` 的整型归一）。

## 当前实现边界说明

这版方案已经落成统一结构：

- `turn_understanding_service` 负责单轮理解
- `profile_collection_policy` 负责动作边界
- `ChatService` 只负责编排、状态副作用和兼容入口

截至当前实现，`turn_understanding_service` 已经内收：

- turn type / subtype / secondary signals
- context ack type / payload
- complaint / boundary / withdraw / risk / opening / service confirmation 判断
- deterministic slot resolve
- extraction guards
- contact candidate 提取
- lightweight / opening profile ack 素材

当前实现里已经没有 `ChatService._xxx` 级别的理解兼容桥。

仍然存在的依赖只剩 understanding 对底层领域服务的正常调用，例如：

- `user_question_service`
- `expectation_service`
- contact 偏好相关的本地规则常量

这些属于正常领域依赖，不是第二套理解逻辑。

## 后续开发硬约束

1. 新增单轮输入识别规则，优先放到 `turn_understanding_service`
2. 新增动作边界规则，优先放到 `profile_collection_policy`
3. `ChatService` 不再新增新的用户意图识别逻辑
4. 不允许再新增第二套 `followup_topic / context_ack / complaint / faq intent` 平行判断
5. 如需替换桥接来源，只允许改 understanding 内部私有 helper，不允许外层直接回调 `chat_service._xxx`

## 文件清单

当前与该方案强相关的文件包括：

- `docs/08_OPENING_GUARD_DESIGN.md`
- `docs/09_TURN_UNDERSTANDING_REFACTOR_DESIGN.md`
- `src/modules/conversation/domain/turn_understanding_service.py`
- `src/modules/conversation/domain/turn_understanding_models.py`
- `src/modules/profile_collection/domain/profile_collection_policy.py`
- `src/modules/conversation/application/process_chat_turn.py`
- `src/services/core/chat_service.py`
- `tests/unit/test_turn_understanding_service.py`
- `tests/unit/test_chat_service_text_helpers.py`
- `tests/unit/test_chat_service_opening_helpers.py`
- `tests/unit/test_chat_service_bridge_helpers.py`
- `tests/unit/test_chat_service_summary_helpers.py`
- `tests/unit/test_chat_service_followup_helpers.py`
- `tests/unit/test_dialogue_manager_prompt_helpers.py`
- `tests/unit/test_dialogue_expression_helpers.py`
- `tests/unit/test_process_chat_turn_use_case.py`
- `tests/unit/test_chat_service_regressions.py`

## 维护口径

后续如果出现：

- FAQ 误判
- boundary / complaint / withdraw 判错
- opening subtype 不稳
- 复合资料漏拆
- contact candidate 误收

优先排查顺序应当是：

1. `turn_understanding_service`
2. `profile_collection_policy`
3. `minimal guard`

而不是回到 `ChatService` 主链直接补 if。

## 最终结论

最终方案不是“少做步骤”，而是：

- 让 Understanding 只管任务与字段
- 让 Policy 只管动作边界
- 让 AI 保持表达自由
- 让 Output Guard 只做最小纠偏

一句话总结：

**统一理解和决策，不统一表达内容；收口逻辑，不收走人味。**
