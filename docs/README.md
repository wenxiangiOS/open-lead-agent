# Docs 导航（唯一入口）

本目录文档较多。后续你本人或其他模型协作时，先看本文件，再按顺序阅读。

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

## 3. 测试与回归

1. `docs/real_ai_policy_regression.md`
2. `docs/testing_layout.md`
3. `docs/guides/TESTING_GUIDE.md`

## 4. 工程结构与治理（参考）

这些文档偏历史治理与结构说明，不是当前主链路执行入口：

- `docs/project_structure.md`
- `docs/service_boundaries.md`
- `docs/services_reorg_plan.md`
- `docs/unused_subsystems_review.md`
- `docs/archive_strategy.md`
- `docs/open_questions.md`

## 5. 给其他模型的最短指令

可直接复制：

`先读 docs/README.md，再按 docs/message_queue_design.md -> docs/message_queue_status.yaml -> reports/mq/*.md 的顺序执行；改完后同步更新 status 和验收报告。`
