# Docs 导航（唯一入口）

本目录文档较多。后续你本人或其他模型协作时，先看本文件，再按顺序阅读。

## 🚨 发布先看（第一入口）

每次发布前，先按这份流程清单逐项执行：

1. `docs/00_ALIYUN_RELEASE_CHECKLIST.md`
2. `docs/00_ALIYUN_RELEASE_RECORD_TEMPLATE.md`（发布执行记录模板）

说明：这是发布前唯一执行版清单，按顺序走，不跳步。

## 0. 当前权威文档

如果你要判断“项目现在真实做到哪里”，优先看这些：

1. `docs/project_status_summary.md`
2. `docs/refactor_execution_plans.md`
3. `docs/compat_cleanup_plan.md`
4. `docs/message_queue_design.md`
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

1. `docs/message_queue_design.md`  
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
3. `message_queue_design.md` 的人工摘要段落

## 2. 资料收集与对话规则

1. `docs/contact_collection.md`（规则权威）
2. `docs/ai_dialog_policy.md`（策略与拟人化原则）
3. `docs/contact_collection_cheatsheet.md`（速查，不作为规则源）

## 2.1 当前权威类

这些文档用于判断“当前项目实际状态”：

- `docs/project_status_summary.md`
- `docs/refactor_execution_plans.md`
- `docs/compat_cleanup_plan.md`

## 2.2 规则文档

这些文档描述业务规则或实施规范：

- `docs/message_queue_design.md`
- `docs/IMPLEMENTATION_TASKS.md`
- `docs/contact_collection.md`
- `docs/ai_dialog_policy.md`
- `docs/contact_collection_cheatsheet.md`

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

## 5. 给其他模型的最短指令

可直接复制：

`先读 docs/README.md，再按 docs/message_queue_design.md -> docs/message_queue_status.yaml -> reports/mq/*.md 的顺序执行；改完后同步更新 status 和验收报告。`
