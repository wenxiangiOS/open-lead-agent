# Prompt 优化改动提交执行单

更新时间：2026-03-21

## 1. 提交策略
- Commit A：代码与测试（功能变更）
- Commit B：文档与脚本（运维与流程）

## 2. Commit A（代码与测试）

```bash
cd /Users/eric/Desktop/doubao_mcp_server
git add \
  src/services/prompts/prompts.py \
  src/services/core/dialogue_manager.py \
  src/services/core/chat_service.py \
  src/modules/conversation/application/process_chat_turn.py \
  src/modules/profile_collection/domain/extraction_service.py \
  src/models/user_profile.py \
  tests/unit/test_chat_service_regressions.py \
  tests/unit/test_extraction_service.py \
  tests/unit/test_user_profile_age_normalization.py

pytest -q tests/unit/test_chat_service_regressions.py tests/unit/test_extraction_service.py tests/unit/test_user_profile_age_normalization.py

git commit -m "feat(dialogue): simplify prompt, add turn observability and dynamic token caps"
```

## 3. Commit B（文档与脚本）

```bash
cd /Users/eric/Desktop/doubao_mcp_server
git add \
  docs/00_00_README.md \
  docs/00_ALIYUN_RELEASE_CHECKLIST.md \
  docs/04_ALIYUN_RELEASE_RECORD_TEMPLATE.md \
  docs/prompt_optimization_final_plan.md \
  docs/01_ALIYUN_OBS_ALERT_PLAYBOOK.md \
  docs/02_ALIYUN_SLS_ALERT_SETUP.md \
  docs/03_REPORT_AUTOMATION.md \
  reports/INDEX.md \
  scripts/generate_report_index.py \
  scripts/run_release_preflight.sh

git commit -m "docs(ops): add aliyun observability playbooks and release preflight/report index workflow"
```

## 4. 发布前一键预检

```bash
cd /Users/eric/Desktop/doubao_mcp_server
bash scripts/run_release_preflight.sh
```

## 5. 仅文档回滚（如需）

```bash
cd /Users/eric/Desktop/doubao_mcp_server
git revert <CommitB哈希>
```

## 6. 整体回滚（如需）

```bash
cd /Users/eric/Desktop/doubao_mcp_server
git revert <CommitB哈希>
git revert <CommitA哈希>
```
