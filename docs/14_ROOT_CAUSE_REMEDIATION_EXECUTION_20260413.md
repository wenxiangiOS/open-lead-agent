# 14 根因级修复执行单（2026-04-13）

## 目标

针对真实回放中暴露的 3 类根因问题做架构级修复，而不是继续补丁：

1. 高风险字段“识别到了但不提交”，导致重复追问、像没记忆。
2. complaint/boundary 走固定短路模板，出现空悬话术和脚本感。
3. 决策、落库、展示对“已提交字段”口径不一致，导致状态断裂。

## 执行范围

本轮执行覆盖：

1. 统一理解主链：资料收集答案轮默认同步启用 AI 结构化，而不是只在少数高风险追问场景启用。
2. AI `direct_write` 提交契约：AI 已明确区分本人信息/择偶要求时，accepted 字段必须直接入主档。
3. 正式写库收口：`persistence_plan.accepted_fields` 成为唯一正式写库输入，旧 extraction 不再重判 self/partner 语义。
4. pre-generation backfill 降权：上下文补识别只能影响回复与恢复主线，不能直接追加 committed 写库字段。
5. complaint/boundary：默认改为模型生成，不再固定模板短路。
6. response plan：新增修复模式约束，强制“承认 + 降压 + 可执行下一步”。

## 开关与默认值

1. `UNIFIED_TURN_SYNC_AI_HIGH_RISK_ENABLED`：默认开启。
2. `MQ_MODEL_GENERATED_REPAIR_ENABLED`：默认开启。

## 验收口径

1. 用户在职业追问轮回复“在编教师”，如果 AI 给出 `direct_write`，则必须直接入库，不再被后链路丢失。
2. 用户一句话同时包含本人资料和择偶要求时，AI 已区分出的字段必须按 `self/partner` 分别落档，不允许后链路串槽。
3. pre-generation backfill 不再向 `persistence_plan.accepted_fields` 注入 committed 字段。
4. complaint 轮不再出现 `prompt_chars=0` 的模板短路。
5. complaint 回复禁止“空悬收口”句式，必须包含可执行下一步。
6. 已提交高风险字段在同轮后续决策可见，不再重复追问同字段。
7. 保持现有联系方式格式校验和状态机不回退。

## 关联文档

1. `docs/10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md`
2. `docs/11_AI_RESPONSE_UNIFIED_GENERATION_DESIGN.md`
3. `docs/conversation_humanlike_execution_spec.md`

## 追加执行（第三阶段：状态确认冲突治理）

本次继续落地以下 3 项，目标是解决“用户已给具体出生年却仍反复追问年龄”的链路冲突：

1. `status_confirmation` 降误锁：
   - `TurnPriorityPolicy` 增加出生年确认语义护栏。
   - 当用户消息中出现明确出生年回答（如 `98年/1998年`）时，不再强制锁 `age` 的确认任务。
2. 长句混合轮生年补提取：
   - pre-generation 新增 `birth_year_confirmation_backfill`。
   - 即便该轮已有其它语义进展（如已识别择偶要求），仍可在“具体出生年追问上下文”补回 `age/age_label`。
3. “AI 理解正确但后链路挡掉”修复（age 显式本人标记放行）：
   - 下游高风险放行策略补齐 `age + explicit_self_marker`。
   - 覆盖收口层：`ChatServiceCollectionExtractionService` / `ChatServiceGenerationService` / `ChatService`。

## 新增验收点

1. 用户回复：`98年的，喜欢成熟稳重，多金，身高180+`
   - 不允许再次进入“出生年待确认”循环追问。
   - 本轮决策不应继续锁定 `ask_field=age`。
2. `age` 字段若为 `explicit_self_marker`（非 AI 通道）：
   - 必须可通过高风险落库门，不再被后置规则无差别拦截。
3. 纯 `invalid_input` 短答（如单独 `98的`）：
   - 仍保持原有 `contextual_short_reply_backfill` 路径，不回归。

## 追加执行（第四阶段：对齐可观测性补齐）

为避免“线上看起来像随机问题，实际是对齐链路漂移”长期无感，本阶段补齐 turn 级可观测字段：

1. 在 finalize 对齐链路记录：
   - `ask_field`（本轮决策主追问字段）
   - `asked_fields`（最终回复实际问到的字段）
   - `ask_field_mismatch_detected`（主追问与最终问句不一致）
   - `ask_field_mismatch_rewritten`（是否已在 finalize 被重写修复）
   - `reask_after_commit_detected`（已收集字段被重复追问）
2. 在 `obs.turn` 统一输出上述信号，作为后续聚合比率的基础：
   - `ask_field_mismatch_rate`
   - `re_ask_after_commit_rate`

### 第四阶段验收点

1. 当回复问错字段且被对齐重写时：
   - `ask_field_mismatch=1`
   - `ask_field_rewritten=1`
2. 当 `ask_field` 已在本轮 `all_fields` 收集成功，但最终回复仍追问该字段时：
   - `reask_after_commit=1`
3. 非异常对齐轮次：
   - 上述指标保持 `0`，不影响原有回复主流程。

## 追加执行（第五阶段：同步语义超时治理）

线上复盘显示：`sync ai semantic` 在长句资料轮经常触发 `12s + 9s` 双超时，导致“AI 结构化理解未生效 + 用户感知卡顿”。

本阶段处理：

1. 同步语义超时默认值改为跟主链路超时对齐（优先读取 `UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS`，未配置时回退 `CHAT_AI_TIMEOUT_SECONDS`）。
2. 同步语义重试改为默认关闭（`UNIFIED_TURN_SYNC_AI_RETRY_ENABLED=0`），避免单轮理解失败时额外叠加一次超时阻塞。
3. `.env / .env.example` 补齐同步语义超时配置，便于线上直接调参而非改代码。

### 第五阶段验收点

1. 日志中不再固定出现 `timeout=12.0s`、`timeout=9.0s` 的双失败模式。
2. 当同步语义失败时，单轮理解阻塞时长可控，不再默认追加二次超时。

### 第五阶段补充（结构化输出瘦身）

为治理“模型在结构化提取时生成超长 JSON 导致 60s 仍超时”的问题，补充执行：

1. 同步提取 prompt 改为轻量 schema：
   - `field_observations` 仅强制 `field/value/scope/write_mode`
   - 明确禁止输出 `evidence_text` 整句复述
   - 限制 `field_observations` 最多 8 条
2. 新增同步提取输出预算配置：
   - `UNIFIED_TURN_SYNC_AI_MAX_TOKENS`（默认 `220`）
   - `UNIFIED_TURN_SYNC_AI_REASONING_EFFORT`（默认 `low`）
3. 失败日志增加 `max_tokens / reasoning_effort`，便于线上定位长尾原因。
4. 同步提取输出协议改为“紧凑行格式（`field|scope|write_mode|value|confidence`）+ 本地解析归一”，并保留 JSON 兼容解析兜底，降低模型因严格 JSON 约束导致的长尾与失配。

## 追加执行（第六阶段：同步语义稳定收敛）

针对最新线上问题“`60s` 同步抽取仍超时、且明明有更丰富偏好被弱值覆盖”，本阶段继续落地：

1. 同步抽取 prompt 再次瘦身为极简协议：
   - `system` 固定为“只返回 JSON”
   - `user` 仅包含：`提取JSON模板 + 用户原话 + 最近追问字段`
   - 去掉长上下文注入（fallback slots / 复杂 schema 约束）以降低长尾
2. 同步抽取阻塞上限改为硬封顶：
   - 新增 `UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS`（默认 `20`）
   - 实际超时预算 = `min(UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS, UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS)`
3. 同步抽取支持独立模型路由：
   - 新增 `UNIFIED_TURN_SYNC_AI_MODEL`（留空时沿用 `MODEL_NAME`）
4. 新增“空抽取保护”：
   - AI 若仅返回 domain、无字段观测（`field_observations/items` 为空），本轮直接视为无效并回退 fallback，不再覆盖已有可用语义
5. 修复“弱值覆盖强值”：
   - `partner_requirement` 不再因早期弱提取（如仅 `身高180+`）短路后续 richer 解析
   - 启用“更丰富择偶要求优先”合并策略，优先保留包含更多偏好要点的值（如 `90后 + 工作稳定 + 身高`）

### 第六阶段验收点

1. 同一句长资料消息连续 3 次回放，同步抽取应稳定落在可接受时延内（本地实测约 `10~12s`）。
2. AI 抽取返回空字段时，最终语义必须自动回退到 fallback，不允许出现“AI成功但收集为空”。
3. 复合择偶偏好（如 `90后工作稳定，180+`）不再被单一弱值长期覆盖。

## 追加执行（第七阶段：字段别名归一与落库兜底）

针对线上出现的“同一句资料有时能识别深圳、有时 `location` 丢失”的抖动，本阶段补充：

1. 增强 AI 字段别名归一：
   - 新增 `residenceCity/currentCity/livingCity` -> `location`
   - 新增 `交友需求/对象需求/需求` -> `partner_requirement`
   - 补充 camelCase 与下划线变体的规范化匹配
2. 增强 `field_observations` 解析兜底：
   - 当 `normalized_value` 缺失时回退 `value`
   - 当 `scope` 缺失或非法时按字段自动推断 scope（`self/partner/contact`）
3. 补充单测覆盖：
   - `residenceCity` 别名应归一为 `location`
   - `normalized_value` 缺失不应导致字段写库丢失

### 第七阶段验收点

1. 首轮长资料输入中，`location=深圳` 在 `semantic_frame` 与最终 `collected_info` 均应稳定可见。
2. 不再出现“字段已被 accepted，但因别名或空 normalized 导致落库失败”的静默丢失。
