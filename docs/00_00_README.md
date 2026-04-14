# Docs 导航（总入口）

本文档是整个 `docs/` 目录的总入口，阅读顺序永远从这里开始。

本文档只负责回答 4 个问题：

1. 现在先看哪份文档
2. 哪份文档是当前规则真相
3. 哪份文档是上线执行清单
4. 哪些文档只是补充材料或历史材料

注意：

- `docs/00_00_README.md` 是导航入口，不是业务规则真相文档
- 上线执行以 `00-04` 为准
- 资料收集与 AI 对话主设计以 `05_PROFILE_COLLECTION_STRATEGY.md` 为准
- 联系方式规则以 `06_CONTACT_COLLECTION.md` 为准
- 消息队列主设计以 `07_MESSAGE_QUEUE_DESIGN.md` 为准

## 🚩 最前必读顺序（发布/上线）

先看下面 6 个文档，按顺序执行：

1. `docs/00_ALIYUN_RELEASE_CHECKLIST.md`
2. `docs/01_ALIYUN_OBS_ALERT_PLAYBOOK.md`
3. `docs/02_ALIYUN_SLS_ALERT_SETUP.md`
4. `docs/03_REPORT_AUTOMATION.md`
5. `docs/04_ALIYUN_RELEASE_RECORD_TEMPLATE.md`（可选，发布留痕）
6. `docs/05_PROFILE_COLLECTION_STRATEGY.md`

说明：
- 如果你当前要理解项目主设计，重点看第 6 个。
- 如果你当前在做上线准备，先看前 4 到 5 个。
- 如果你当前还没上阿里云，至少先看第 1 个和第 6 个。

发布前一键顺序执行命令（最前入口，直接复制）：

```bash
bash scripts/run_release_preflight.sh
```

质量上限门禁（拟人化/对话质量/提取准确度优先）：

```bash
bash scripts/run_quality_upper_bound_gate.sh
```

报告索引（统一查看所有最新报告）：

```bash
python3 scripts/generate_report_index.py
```

查看路径：`reports/INDEX.md`

说明：脚本会按顺序执行质量门禁、MQ ingest 回归、MQ 压测门禁，并自动刷新 `reports/INDEX.md`。

全场景单命令测试（自动识别问题）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```

说明：
- 自动读取 `reports/real_ai_realism/latest.json` 做基线对比（若存在）。
- 自动输出“项目健康门禁” PASS/FAIL 和失败项（拟人化/提取/时延/模板风险/隔离等）。
- 自动补充 MQ ingest 检查（可用 `--no-include-mq-checks` 关闭）。
- 自动生成：
  - `reports/latest_summary.txt`
  - `docs/next_fix_todo.md`

快速模式（同一命令，缩短时长）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose --fast
```

本目录文档较多。后续你本人或其他模型协作时，先看本文件，再按顺序阅读。

## 目录分工

为了避免文档职责混淆，统一按下面方式理解：

- `docs/00_00_README.md`
  目录总入口，只负责导航
- `docs/00-04_*.md`
  上线、发布、告警、报告相关执行文档
- `docs/05_PROFILE_COLLECTION_STRATEGY.md`
  资料收集与 AI 对话主设计
- `docs/06_CONTACT_COLLECTION.md`
  联系方式专项规则
- `docs/07_MESSAGE_QUEUE_DESIGN.md`
  消息队列主设计
- `docs/08_OPENING_GUARD_DESIGN.md`
  开场保护层设计
- `docs/09_TURN_PRIORITY_POLICY_DESIGN.md`
  单轮优先级策略设计
- 其他文档
  作为专题说明、实现细节、运维说明或历史材料

## 🚨 发布先看（第一入口）

每次发布前，先按这份流程清单逐项执行：

1. `docs/00_ALIYUN_RELEASE_CHECKLIST.md`
2. `docs/04_ALIYUN_RELEASE_RECORD_TEMPLATE.md`（发布执行记录模板，可选）

说明：这是发布前唯一执行版清单，按顺序走，不跳步。

发布前一键回归命令同上，建议优先使用顶部这条单行版本。

## 0. 当前权威文档

如果你要判断“项目现在真实做到哪里”，优先看这些：

1. `docs/project_status_summary.md`
2. `docs/refactor_execution_plans.md`
3. `docs/compat_cleanup_plan.md`
4. `docs/07_MESSAGE_QUEUE_DESIGN.md`
5. `docs/message_queue_status.yaml`

说明：

- `docs/archive/` 下的文档默认视为历史材料，不代表当前现状
- `docs/archive/reorg/` 下的结构类文档已经归档，不应作为当前架构真相

## 0.1 文档分类总览

当前 `docs/` 根目录建议按下面方式理解：

- 当前权威
  - 项目现状、重构状态、兼容层清理状态
- 规则文档
  - 联系方式、对话策略、消息队列实现规范
- 运维与测试
  - runbook、回归入口、测试布局
- 历史或补充
  - archive 策略、未接入子系统评审、开放问题

如果文档与代码冲突，优先级建议：

1. 测试结果与实际代码
2. `project_status_summary.md`
3. `refactor_execution_plans.md`
4. `compat_cleanup_plan.md`
5. 其他专题文档

## 1. 消息队列功能（当前主线）

固定顺序：

1. `docs/07_MESSAGE_QUEUE_DESIGN.md`  
   目标、边界、实现方案、验收标准（主规范）
2. `docs/message_queue_status.yaml`  
   当前执行状态（P0/P1/P2 是否完成、还有哪些 open items）
3. `reports/mq/*.md`  
   验收证据（测试命令与结果）
4. `docs/message_queue_runbook.md`  
   故障处理与运维操作

结论优先级：

1. 验收报告与测试结果
2. `message_queue_status.yaml`
3. `07_MESSAGE_QUEUE_DESIGN.md` 的人工摘要段落

## 2. 资料收集与对话规则

1. `docs/05_PROFILE_COLLECTION_STRATEGY.md`（资料收集与 AI 对话主设计）
2. `docs/06_CONTACT_COLLECTION.md`（联系方式规则权威）
3. `docs/08_OPENING_GUARD_DESIGN.md`（开场保护层设计）
4. `docs/09_TURN_PRIORITY_POLICY_DESIGN.md`（单轮优先级策略）
5. `docs/10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md`（统一理解与写库架构）
6. `docs/contact_collection_cheatsheet.md`（速查，不作为规则源）
7. `docs/ai_dialog_policy.md`（迁移说明，不再作为规则源）

## 2.1 当前权威类

这些文档用于判断“当前项目实际状态”：

- `docs/project_status_summary.md`
- `docs/refactor_execution_plans.md`
- `docs/compat_cleanup_plan.md`

## 2.2 规则文档

这些文档描述业务规则或实施规范：

- `docs/07_MESSAGE_QUEUE_DESIGN.md`
- `docs/08_OPENING_GUARD_DESIGN.md`
- `docs/09_TURN_PRIORITY_POLICY_DESIGN.md`
- `docs/10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md`
- `docs/14_ROOT_CAUSE_REMEDIATION_EXECUTION_20260413.md`
- `docs/IMPLEMENTATION_TASKS.md`
- `docs/05_PROFILE_COLLECTION_STRATEGY.md`
- `docs/06_CONTACT_COLLECTION.md`
- `docs/ai_dialog_policy.md`
- `docs/contact_collection_cheatsheet.md`

补充说明：

- `docs/05_PROFILE_COLLECTION_STRATEGY.md` 是资料收集与 AI 对话统一主策略真相，负责字段覆盖、画像充分度、轮次节奏、答疑恢复、联系方式冻结与成本控制。
- `docs/06_CONTACT_COLLECTION.md` 是联系方式流程真相，负责电话/微信状态机与“上游 gate 通过后如何进入联系方式”。
- `docs/ai_dialog_policy.md` 仅保留迁移说明，避免旧引用失效。

## 3. 运维与测试

1. `docs/real_ai_policy_regression.md`
2. `docs/testing_layout.md`
3. `docs/message_queue_runbook.md`
4. `docs/guides/TESTING_GUIDE.md`

## 3.1 外部系统接入（新增）

如果你要和第三方平台做接口对接，先看：

1. `docs/external_integration_guide.md`
2. `docs/external_integration_quickstart.md`

该文档覆盖：

- 同步模式：`/api/doubao/chat`
- 异步模式：`/api/xiaohongshu/messages/ingest` + 回调/轮询
- 请求响应示例、鉴权、幂等、重试与迁移建议
- 一页式接入清单（适合直接发实施同学）

常用命令（直接复制）：

- Chat 场景回归（默认，不含 mq）  
  `python3 scripts/run_real_ai_regression.py`
- MQ ingest 场景回归（仅 mq）  
  `python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000`
- 全量回归（chat + mq，一条命令）  
  `python3 scripts/run_real_ai_regression.py --include-mq --mq-base-url http://127.0.0.1:8000`

## 3.2 报告自动化（新增）

- 文档：`docs/03_REPORT_AUTOMATION.md`
- 作用：定时自动刷新 `reports/INDEX.md`，避免遗忘报告入口。

## 4. 历史或补充文档

这些文档偏治理、补充说明或历史记录，不是当前主链路执行入口：

- `docs/unused_subsystems_review.md`
- `docs/archive_strategy.md`
- `docs/open_questions.md`
- `docs/archive/reorg/project_structure.md`
- `docs/archive/reorg/service_boundaries.md`
- `docs/archive/reorg/services_reorg_plan.md`
- `docs/archive/architecture/ARCHITECTURE_REVIEW.md`
- `docs/archive/architecture/OPTIMIZATION_SUMMARY.md`
- `docs/PROMPT_OPTIMIZATION_COMMIT_RUNBOOK.md`

## 5. 给其他模型的最短指令

可直接复制：

`先读 docs/00_00_README.md，再按 docs/07_MESSAGE_QUEUE_DESIGN.md -> docs/message_queue_status.yaml -> reports/mq/*.md 的顺序执行；改完后同步更新 status 和验收报告。`
