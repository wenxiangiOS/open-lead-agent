# Prompt 与对话系统最终优化方案（含阿里云上线排障）

## 1. 目标与验收标准

### 1.1 目标
- 提升拟人化：降低模板感、公告腔、机械追问。
- 提升对话质量：降低答非所问、重复追问、字段错提取。
- 提升逻辑稳定：统一优先级，减少规则冲突。
- 提升性能与成本：降低 Prompt 体积、P95、超时率和单会话成本。
- 提升可运营性：形成自动评估、自动告警、自动回滚闭环。

### 1.2 验收阈值（建议）
- 自然承接命中率 >= 85%。
- 高冲突槽位错位率 <= 2%。
- 重复追问率下降 >= 40%。
- P95 时延下降 >= 20%。
- 超时率下降 >= 30%。

## 2. 现状问题总结
- `MAIN_DIALOGUE` 规则过长、重复、冲突密度高，推理负担大。
- Prompt 与代码护栏存在双重约束，导致冗余推理。
- 对话与抽取合并单调用，Prompt 体积直接影响时延。
- 年龄等抽取口径在提示词、解析、测试样例间不一致。
- 欢迎语存在系统痕迹，降低拟人化沉浸感。

## 3. 总体架构升级
- 从“长 Prompt 主导”升级为“策略引擎主导 + 轻 Prompt 执行”。
- 服务层先生成结构化 `turn_plan`，模型负责自然表达与结构化抽取。
- 高风险场景优先规则化处理，普通场景再走生成模型。
- 抽取口径统一，提示词/解析/入库使用同一数据契约。
- 建立“离线仿真 -> 在线实验 -> 版本治理 -> 自动回滚”闭环。

## 4. Prompt 重构方案

### 4.1 四层模板
- `base_persona`：角色、语气、合规红线（短文本常驻）。
- `turn_policy`：本轮目标、可问字段、禁问字段。
- `scenario_block`：离异/分居、答疑优先、联系方式门控，仅命中注入。
- `output_contract`：自然回复 + `<extract>` 输出契约。

### 4.2 改造原则
- 删除重复规则与高密度警示符号（如连续 ⚠️/🚫）。
- 仅保留真正红线为“必须/禁止”，其他改为“优先策略”。
- 欢迎语去系统暴露文案，不出现“系统自动发送”。
- 常规轮不再注入全量规则，只注入当前轮必需片段。

## 5. 对话策略引擎（turn_plan）

### 5.1 结构字段
- `main_target`
- `side_target`
- `must_answer_question`
- `blocked_fields`
- `can_enter_contact`
- `risk_level`
- `tone_level`

### 5.2 关键规则
- FAQ/顾虑轮只答疑，不推进资料收集。
- 追问统一为 1-2-3 机制：正常问 -> 换角度+简短解释 -> 跳过。
- 联系方式阶段与普通资料阶段解耦，不抢优先级。
- 高风险输入优先固定护栏，不让模型自由发挥。

## 6. 抽取口径统一

### 6.1 年龄
- `age` 存数值。
- `age_label` 存原始表达（如 90后/95后）。

### 6.2 高冲突槽位
- “我在/我是XX的” -> `location`。
- “想找XX的” -> `partner_requirement`。
- 择偶语境中的数字/学历/身高优先提取到 `partner_requirement`。

### 6.3 保守策略
- 不确定值置 `null`，不强行推断。
- 清理提示词示例与解析逻辑冲突项。
- 清理未使用参数与无效占位。

## 7. 性能与成本优化
- 将主 Prompt 体积压缩到当前 50%-65%。
- 场景块按需拼接，减少无效 token。
- 按轮次动态 `max_tokens`：常规轮低、复杂轮高。
- 强化快路径：短答资料轮优先规则/快模型。
- 高风险轮固定主模型，保证稳定与合规。

## 8. 拟人化专项优化
- 引入 `tone_level`（谨慎型/配合型/高意向型）。
- 默认“先承接再推进”，限制每轮问题数。
- 模板去重：近 N 轮避免同句复用。
- 结束意图策略改为“尊重优先，一次挽留封顶”。

## 9. 高阶持续优化（自动化）

### 9.1 策略自学习（系统自动）
- 每周从历史高质量对话生成候选策略。
- 候选策略不直接生效，先进入评估与审批。

### 9.2 实时个性化（系统自动）
- 根据用户当轮反馈动态调整 `tone_level`、追问强度、解释长度。
- 通过参数边界控制最大说服强度与最大追问次数。

### 9.3 自动回归与发布守门（系统自动）
- 每日自动回归。
- 每次发版自动比对红线指标。
- 红线触发自动阻断发布或自动回滚。

### 9.4 分层与长期价值
- 细分用户分层（来源、城市、活跃度、历史反馈）。
- 策略自动淘汰低收益版本，防止策略膨胀。
- 监控长期指标：复聊率、留存、后续匹配成功率。

## 10. 指标与评估体系

### 10.1 拟人化
- 承接命中率
- 模板复读率
- 公告腔占比

### 10.2 质量
- 字段错位率
- 重复追问率
- 答非所问率
- 用户中断率

### 10.3 逻辑
- 优先级冲突率
- 流程违规率

### 10.4 性能
- 首字时延
- P50/P95
- 超时率
- 空响应率
- token/会话

## 11. 发布、灰度、回滚
- 灰度策略：10% -> 50% -> 全量。
- 每阶段至少观察 30-60 分钟核心指标再升量。
- 保留旧 Prompt 开关、旧路由开关、旧模型开关。
- 任一红线超阈值立即回切并告警。

## 12. 阿里云上线排障与应急手册

### 12.1 上线前必备
- 每个请求全链路打 `request_id/account_id/dialog_id`。
- 阶段耗时日志：`build_prompt`、`AI_call`、`extract_parse`、`profile_update`。
- 关键状态日志：`route`、`model`、`prompt_chars`、`timeout`、`fallback`。
- 建议统一单行日志格式（已实现 `obs.turn`）：`trace_id/account_id/dialog_id/route/response_channel/prompt_chars/extracted_fields/total_ms/stages/error`。

### 12.2 监控与告警
- 日志：阿里云 SLS。
- 指标：ARMS/Prometheus（QPS、5xx、P95、超时率、空回复率、提取失败率）。
- 告警通道：钉钉/飞书/企微 + 邮件兜底。

### 12.3 线上问题排查顺序
1. 看告警时段错误率与 P95 是否异常。
2. 用 `request_id` 回溯单请求全链路日志。
3. 定位层级：网关/应用/AI调用/提取解析/Redis-DB。
4. 对照该请求的 `route/model/prompt_version` 是否异常变更。

### 12.4 高频故障定位指引
- 回复慢：看 `AI_call` 耗时、`prompt_chars` 是否异常增大。
- 回复错：看 `<extract>` 原文、解析映射、字段冲突规则。
- 不回复：看超时、空响应、fallback 是否触发。
- 局部人群异常：看分层路由与 `turn_plan` 命中逻辑。

### 12.5 应急操作
- 一键切回旧 Prompt 版本。
- 关闭快路径路由，强制主模型。
- 降级到固定模板答复（高峰期兜底）。
- 执行变更冻结，待指标恢复后再逐步恢复灰度。

## 13. 实施计划（14天）
- D1-D3：Prompt 四层重构与精简。
- D4-D6：`turn_plan` 接管流程决策。
- D7-D8：抽取口径统一与冲突修复。
- D9-D10：性能调优与路由阈值优化。
- D11：自动回归、看板与告警接入。
- D12：10% 灰度。
- D13：50% 灰度。
- D14：全量发布与复盘。

## 14. 你后续怎么使用
- 系统自动：实时个性化、回归、告警、候选策略生成。
- 你负责：阈值配置、候选审批、灰度升量、回滚决策。
- 日常只需关注：周报、异常告警、发版门禁结果。
- 发布前统一执行：`bash scripts/run_release_preflight.sh`。
- 报告查看统一入口：执行 `python3 scripts/generate_report_index.py`，然后查看 `reports/INDEX.md`。

## 15. 预期收益区间（基于当前代码形态）
- 拟人化：提升约 20%-40%。
- 对话质量：提升约 25%-45%。
- 逻辑稳定性：提升约 30%-50%。
- P95 时延：改善约 15%-30%。

## 16. 相关代码与文档（落地参考）
- `src/services/prompts/prompts.py`
- `src/services/core/dialogue_manager.py`
- `src/services/core/chat_service.py`
- `src/modules/conversation/application/process_chat_turn.py`
- `src/modules/profile_collection/domain/extraction_service.py`
- `tests/manual/main_dialogue_humanlike_checks.md`
- `tests/manual/extraction_regression_cases.json`
- `docs/01_ALIYUN_OBS_ALERT_PLAYBOOK.md`
- `docs/02_ALIYUN_SLS_ALERT_SETUP.md`
- `docs/03_REPORT_AUTOMATION.md`

## 17. 推荐环境变量（上线可直接配置）

### 17.1 AI 路由与长度控制
- `AI_ROUTING_ENABLED=true`
- `AI_FAST_MODEL_NAME=<你的快模型>`
- `CHAT_AI_MAX_TOKENS=420`
- `CHAT_AI_LOW_COMPLEXITY_MAX_TOKENS=260`
- `CHAT_AI_HIGH_RISK_MAX_TOKENS=180`
- `CHAT_AI_LONG_PROMPT_CHAR_THRESHOLD=6500`
- `CHAT_AI_LONG_PROMPT_MAX_TOKENS=220`

### 17.2 超时控制
- `CHAT_AI_TIMEOUT_SECONDS=18`
- `CHAT_AI_HARD_TIMEOUT_SECONDS=22`

### 17.3 追问冷却
- `MQ_FIELD_ASK_COOLDOWN_TURNS=2`

### 17.4 发布建议
- 灰度阶段先将 `CHAT_AI_MAX_TOKENS` 设为 380 观察 24h。
- 若用户答疑完整性下降，再提升到 420 或调高复杂轮阈值。

## 18. 落地状态矩阵（必须读）

状态说明：
- `已实现`：代码或脚本已落地，可直接使用。
- `部分实现`：已有基础能力，但不是方案完整形态。
- `未实现`：仅有方案/文档，尚未进入代码执行链路。

### 18.1 核心能力状态
- Prompt 精简与去系统腔：`已实现`  
  代码：`src/services/prompts/prompts.py`
- `turn_plan_instruction` 注入 Prompt：`已实现`  
  代码：`src/services/core/dialogue_manager.py`
- 抽取口径统一（年龄/出生年）：`已实现`  
  代码：`src/modules/profile_collection/domain/extraction_service.py`、`src/models/user_profile.py`
- 动态 `max_tokens`：`已实现`  
  代码：`src/services/core/chat_service.py`
- `obs.turn` 可观测日志：`已实现`  
  代码：`src/modules/conversation/application/process_chat_turn.py`
- 回归测试补齐：`已实现`  
  测试：`tests/unit/test_chat_service_regressions.py`、`tests/unit/test_extraction_service.py`、`tests/unit/test_user_profile_age_normalization.py`

### 18.2 方案高阶项状态
- 四层模板完整拆分（`base_persona/turn_policy/scenario_block/output_contract`）：`部分实现`  
  说明：当前是“精简 + 按需注入”，尚未拆成独立模板文件与装配器。
- 策略自学习（周更候选策略 + 审批流）：`未实现`
- 实时个性化自动调参：`未实现`
- 自动回滚联动（告警触发自动回切）：`未实现`
- 线上灰度实验（10%/50%/100%）：`未实现`（依赖线上环境）

## 19. 未实现项如何实现（给后续模型/同学）

### 19.1 四层模板完整拆分（当前 `部分实现`）
1. 新建目录：`src/services/prompts/templates/`，拆分 `base_persona.py`、`turn_policy.py`、`scenario_block.py`、`output_contract.py`。
2. 新建装配器：`src/services/prompts/prompt_assembler.py`，按 `turn_plan` 命中动态拼装。
3. 改造 `dialogue_manager` 调用装配器，删除 `prompts.py` 中冗长拼接逻辑。
4. 增加模板快照测试，确保不同路由的 Prompt 长度和字段稳定。

### 19.2 策略自学习（当前 `未实现`）
1. 新增离线任务脚本：`scripts/build_policy_candidates.py`（从历史高质量对话提炼候选策略）。
2. 新增候选库存储：`data/policy_candidates/*.json`（含版本、来源、收益估计、风险标签）。
3. 新增审批开关：`POLICY_CANDIDATE_VERSION`，只允许“已审批版本”进入线上。
4. 将候选策略接入回归脚本，未过门禁禁止启用。

### 19.3 实时个性化（当前 `未实现`）
1. 在 `turn_decision` 增加可控参数：`tone_level`、`ask_strength`、`explain_length`。
2. 参数必须有硬边界：最大追问次数、最大说服强度、联系方式推进冷却。
3. 增加实验开关：`AI_PERSONALIZATION_ENABLED`，默认关闭。
4. 先离线回放，再小流量灰度。

### 19.4 自动回滚联动（当前 `未实现`）
1. 在告警平台配置 webhook，触发回滚脚本（或发布平台 API）。
2. 设定红线：错误率、P95、空回复率、抽取异常率。
3. 引入回滚保护：最短间隔、人工确认白名单、回滚后冻结窗口。
4. 回滚动作必须写审计日志（谁触发、何时触发、回切版本）。

### 19.5 线上灰度（当前 `未实现`）
1. 准备三组流量规则：10% -> 50% -> 100%。
2. 每阶段观察至少 30-60 分钟核心指标。
3. 任一红线超阈值立即停止升量并回切。
4. 发布完成后更新 `docs/04_ALIYUN_RELEASE_RECORD_TEMPLATE.md` 留痕。

## 20. 给后续模型的执行入口（必读）

如果你是后续接手模型，请按以下顺序执行：
1. 先读：`docs/README.md` 顶部“最前必读顺序”。
2. 再读：本文件第 18 节“落地状态矩阵”，确认哪些是 `未实现`。
3. 按第 19 节逐项落地，且每完成一项就更新本节状态（`未实现 -> 部分实现 -> 已实现`）。
4. 每次改动后至少执行：  
   `pytest -q tests/unit/test_chat_service_regressions.py tests/unit/test_extraction_service.py tests/unit/test_user_profile_age_normalization.py`
5. 跑完回归后执行：`python3 scripts/generate_report_index.py` 并更新 `reports/INDEX.md`。

补充（单命令全场景识别）：
- 使用 `python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose` 时，
  脚本会自动尝试读取 `reports/real_ai_realism/latest.json` 做基线对比，并输出“项目健康门禁”失败项。
- 同命令现已支持：
  - `--fast` 快速模式（关键场景优先）
  - 分级门禁（P0/P1/P2）
  - 自动补充 MQ ingest 检查
  - 自动输出 `reports/latest_summary.txt` 与 `docs/next_fix_todo.md`
