# 真实 AI 场景回归

这套测试用于跑真实 `AIService + ChatService` 端到端链路，不 mock 模型回复。

## 最优先命令

如果你要测试下面两份文档合并后的完整方案：

- `docs/05_PROFILE_COLLECTION_STRATEGY.md`
- `docs/06_CONTACT_COLLECTION.md`

最优先直接运行这条核心场景命令：

```bash
python3 scripts/run_profile_contact_full_regression.py --scenario-pack core84 --verbose
```

这条命令会一次性跑：

1. `05_PROFILE_COLLECTION_STRATEGY.md` 对应的 63 个核心真实 AI chat 场景
2. `06_CONTACT_COLLECTION.md` 对应的 21 个真实 AI 联系方式集成场景
3. 两份方案联动后的核心完整真实 AI 效果

如果你当前只看一个命令，就看这条。

如果你要跑**全量完整方案回归**，再运行：

```bash
python3 scripts/run_profile_contact_full_regression.py --verbose
```

这里的 `core84` 是历史名称，当前指的是：

1. `05_PROFILE_COLLECTION_STRATEGY.md` 对应的 74 个核心 chat 场景
2. `06_CONTACT_COLLECTION.md` 对应的 21 个真实 AI 联系方式集成场景

合计：

- **95 个真实 AI 场景**

## 目录结构

- `tests/real_ai/scenario_runner.py`
  统一场景执行器、断言器、报告输出。
- `tests/real_ai/scenarios/*.json`
  chat 场景定义文件，建议按专题拆分维护。
- `tests/real_ai/scenarios_pending/*.json`
  待收口场景（含 mq ingest 回归场景）；默认会参与 `--list`。
- `scripts/run_real_ai_regression.py`
  chat 回归命令行入口（可选 `--include-mq` 串行触发 mq runner）。
- `scripts/run_mq_ingest_regression.py`
  mq ingest API 回归命令行入口。

## 运行

推荐首选（真实性仿真）：要看每条用户和 AI 内容，加 `--verbose`

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```

## 05 + 06 完整方案真实 AI 回归（新增主命令）

如果你的目标是一次性验证下面两份文档合并后的完整方案：

- `docs/05_PROFILE_COLLECTION_STRATEGY.md`
- `docs/06_CONTACT_COLLECTION.md`

请优先使用这个命令：

```bash
python3 scripts/run_profile_contact_full_regression.py --verbose
```

这个命令测试的是：

1. `05_PROFILE_COLLECTION_STRATEGY.md` 中资料主线、4 Gate、字段级 outcome、用户疑问优先恢复、`partner_requirement` 兜底、联系方式冻结、`made_effective_progress` 等全部真实 AI 场景。
2. `06_CONTACT_COLLECTION.md` 中电话/微信状态机、用户主动拒绝联系方式、用户主动提供联系方式、AI 主动询问联系方式、香港/非香港差异、双拒结束等全部真实 AI 场景。
3. 两份文档联动后的整体效果，而不是单独模块的假设效果。

它会顺序执行两部分：

1. `tests/real_ai/scenarios/*.json` 中全部非 mq chat 场景
2. `tests/integration/test_contact_collection_integration.py` 中 21 个真实 AI 联系方式集成场景

也就是说，这条命令不是只测聊天，也不是只测联系方式，而是测：

- 资料主策略是否正确
- 联系方式流程是否正确
- 两者交接时的真实 AI 效果是否正确

报告输出目录默认在：

- `reports/real_ai/profile_contact_full/`

其中：

- chat 报告在 `reports/real_ai/profile_contact_full/chat/`
- 总汇总在 `reports/real_ai/profile_contact_full/latest_summary.md`

只查看覆盖范围，不执行：

```bash
python3 scripts/run_profile_contact_full_regression.py --list
```

只跑联系方式 21 场景：

```bash
python3 scripts/run_profile_contact_full_regression.py --skip-chat --verbose
```

只跑某一个联系方式场景，例如 `1.1`：

```bash
python3 scripts/run_profile_contact_full_regression.py --skip-chat --contact-scenario 1.1 --verbose
```


# 方式二：使用真实 AI（联系方式收集 - 真实 AI 自动化测试） 
python tests/integration/test_contact_collection_integration.py --real-ai

质量上限门禁（一键，先跑金标长链再跑全覆盖 strict gate）：

```bash
bash scripts/run_quality_upper_bound_gate.sh
```

失败时会自动：

1. 归档 `reports/real_ai_realism/latest.json|latest.md` 到 `reports/real_ai_realism/gate_failures/`
2. 在终端打印 Top 失败项摘要（turn/policy/field）

说明（默认已开启，不需要额外加参数）：

1. 严格拟人化闸门默认开启（命中关键风险项会返回退出码 1）。
2. 秒回检测默认开启：
`--min-human-latency 0.9`、`--faq-min-human-latency 1.2`。
3. 如果想临时放宽，可加：
`--no-strict-humanlike` 或自行调整上述两个阈值。

报告新增指标（用于“质量优先”优化）：

1. 总耗时（墙钟）、平均每会话耗时、平均每轮耗时、分位时延（p50/p90/p95/p99/max）。
2. 分阶段耗时均值（`ai_call` / `rule_check` / `extract_collect` / `profile_load` / `profile_save` / `response_build`）。
3. 对话自然度：情绪承接命中率、FAQ 非复读率、FAQ 转场自然率、按意图话术多样性。
4. 提问压迫感：连续提问轮次统计（avg/p95/max，>=3 连问占比）。
5. 提取诊断：字段冲突修复率、证据链覆盖率、误提取类型分桶。
6. 联系方式专项：成功率、无效电话/微信未重试次数。
7. 质量护栏：字段稳定性分数、拒绝后尊重率、记忆回用准确率、收尾自然度、异常恢复率。
8. 一致性指标：人设一致性分、动作一致性分。
9. 自动失败样本：按 turn/field/policy 每类自动抽样复现片段。
10. 身份暴露防线：覆盖“你是AI吗/是不是机器人”问法，并在 strict 模式拦截 `ai_identity_exposed`。
11. 异常用户鲁棒性：覆盖乱码、辱骂、污言、反复捣乱，并在 strict 模式拦截 `abuse_not_deescalated`、`nonsense_not_guided`。
12. 高级鲁棒性：覆盖越权请求、隐私套取、多意图冲突、语言混杂，并在 strict 模式拦截 `overreach_not_guarded`、`privacy_internal_leak`。
13. 高风险安全护栏：覆盖法律/医疗越界问询与自伤暗示，并在 strict 模式拦截 `high_risk_advice_overreach`、`safety_signal_not_deescalated`。

发布前基线建议（冻结回归口径）：

1. 固定命令：`python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose`
2. 固定阈值：保留默认 strict（不加 `--no-strict-humanlike`）。
3. 基线文件：将当次通过报告复制为 `reports/real_ai_realism/baseline_release.json|md`，后续发版必须与基线对比不退化。
4. 自动对比：可加 `--baseline-json reports/real_ai_realism/baseline_release.json`，跑完自动输出退化项。
5. strict 灰度回滚：可加 `--strict-ignore-failures a,b,c` 临时忽略指定失败项（建议仅短期使用并留审计记录）。

全覆盖建议执行顺序：

1. chat 真实性回归（默认跑全部非 mq 场景）：  
`python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose`
2. mq 链路回归（20）：  
`python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000`

随机真人风格批量模拟（抽检）：

```bash
python3 scripts/run_random_user_simulation.py --sessions 20 --min-turns 6 --max-turns 12 --seed 42
```

覆盖场景模式（按场景逐个模拟真人式聊天，默认跳过 mq）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --max-scenarios 117 --seed 42 --verbose
```

完整覆盖（按场景逐个模拟，输出时延异常与模板化风险）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```

逻辑硬回归（原有）：

列出当前场景源中的所有场景（含 chat + mq）：

```bash
python3 scripts/run_real_ai_regression.py --list
```

详细模式：

```bash
python3 scripts/run_real_ai_regression.py --verbose
```

运行全部 chat 场景（默认）：

```bash
python3 scripts/run_real_ai_regression.py
```

说明：默认执行 chat 场景（不含 `mq`）。

运行全量（chat + mq）：

```bash
python3 scripts/run_real_ai_regression.py --include-mq --mq-base-url http://127.0.0.1:8000
```

只跑 mq ingest 场景：

```bash
python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000
```

说明：

1. 当前 20 个 mq 场景都已具备 `mq_expect`，不会再因 `missing mq_expect` 被占位跳过。
2. 其中含 `ingest 代理断言` 标记的场景，是基于 ingest 返回字段（如 `status/accepted/cancelLike/seq`）做前置验证，不等同于完整 worker/replies/outbox 端到端验证。

MQ 小并发压测（上线前建议执行）：

```bash
python3 scripts/run_mq_load_test.py \
  --base-url http://127.0.0.1:8000 \
  --accounts 20 \
  --messages-per-account 10 \
  --concurrency 20 \
  --include-dashboard
```

MQ 发布门禁（不达标返回非 0）：

```bash
python3 scripts/run_mq_load_test.py \
  --base-url http://127.0.0.1:8000 \
  --accounts 20 \
  --messages-per-account 10 \
  --concurrency 20 \
  --include-dashboard \
  --gate \
  --max-fail-rate 0.02 \
  --max-p95-ms 400 \
  --max-p99-ms 800 \
  --max-latency-ms 3000 \
  --min-rps 1.0 \
  --max-queue-full-rate 0.5
```

压测输出：

1. 总请求数、HTTP 成功/失败、accepted/queued/duplicate/queue_full 分布。
2. 时延指标：`avg/p50/p90/p95/p99/max`。
3. 吞吐：`rps`。
4. 压测前后 dashboard 快照（`--include-dashboard`）。
5. 门禁结果（`--gate`）：阈值不达标会返回退出码 `1`。

只跑某个分类：

```bash
python3 scripts/run_real_ai_regression.py --category contact
```

只跑某个场景：

```bash
python3 scripts/run_real_ai_regression.py --scenario-id faq_priority_mediator
```

遇到失败就停：

```bash
python3 scripts/run_real_ai_regression.py --stop-on-failure
```

## 场景格式

每个 JSON 文件结构：

```json
{
  "scenarios": [
    {
      "id": "faq_priority_fee",
      "category": "faq",
      "description": "用户问收费时先答疑",
      "messages": ["找对象", "怎么收费"],
      "assertions": [
        { "type": "response_contains_any", "turn": 2, "values": ["免费", "收费"] },
        { "type": "response_not_contains_any", "turn": 2, "values": ["电话", "微信"] }
      ]
    }
  ]
}
```

## 当前支持的断言

- `response_contains_any`
- `response_not_contains_any`
- `final_response_contains_any`
- `final_response_not_contains_any`
- `profile_field_equals`
- `profile_field_not_equals`
- `profile_field_truthy`
- `profile_field_falsey`

## 真实仿真测试方案（新增）

目的：

1. 模拟真人逐句聊天（不是一条消息给完全部信息）
2. 覆盖全部 chat 场景，输出拟人化与稳定性报告
3. 自动定位时延异常轮次与优化空间

输出文件：

1. `reports/real_ai_realism/latest.json`
2. `reports/real_ai_realism/latest.md`

报告包含：

1. 时延分位：`p50/p90/p95/p99/max`
2. 分段耗时均值：`ai_call/profile_load/profile_save/rule_check/context_load/extract_collect/response_build/other`
3. 慢点 Top20（场景ID + 轮次 + 用户输入 + 分段耗时）
4. 模板化风险（Top 模板占比与阈值判定）
5. 字段收集质量（核心字段检查通过率 + 失败明细）
6. 自动优化建议（按瓶颈阶段生成）
7. 对话策略规则质量（追问上限/同字段不连问/低优字段不主动问/月薪降压问法）

## 建议的扩展顺序

1. `contact`：电话、微信、拒绝、香港用户、无效号码
2. `ending`：分居、离异手续未办妥、双拒绝收尾
3. `field_collection`：多字段提取、模糊表达、占位词污染保护
4. `faq`：收费、门店、牵线、照片、联系方式疑问

---

## 联系方式收集专项测试

位于 `tests/integration/test_contact_collection_integration.py`，覆盖 21 个联系方式收集场景。

### 场景列表

| 场景组 | 场景 ID | 描述 |
|-------|---------|------|
| 场景一：用户主动拒绝联系方式 | 1.1 - 1.9 | 拒绝电话、拒绝微信、双拒绝、香港用户拒绝等 |
| 场景二：用户主动提供联系方式 | 2.1 - 2.4 | 主动给电话、主动给微信、同时给等 |
| 场景三：AI 主动询问联系方式 | 3.1 - 3.8 | 先问电话、先问微信、顺序询问等 |

### 运行命令

```bash
# 方式一：使用 FakeAI（默认，快速，离线，适合 CI/CD）
python -m pytest tests/integration/test_contact_collection_integration.py -v



# 方式三：运行指定场景
python tests/integration/test_contact_collection_integration.py --scenario 1.1 --real-ai
python tests/integration/test_contact_collection_integration.py --scenario 3.5 --real-ai

# 列出所有可用场景
python tests/integration/test_contact_collection_integration.py --list
```

### 两种模式对比

| 模式 | FakeAI（默认） | 真实 AI |
|------|---------------|--------|
| 速度 | 快（~0.1秒/场景） | 慢（~10秒/场景） |
| 网络 | 不需要 | 需要联网 |
| Token 消耗 | 0 | 消耗 token |
| 适用场景 | CI/CD、逻辑验证 | 验证实际对话效果 |
| AI 调用耗时 | 0.001秒 | 3-10秒 |

---

## AI 对话策略回归测试（基于 ai_dialog_policy.md）

基于 `docs/ai_dialog_policy.md` 文档定义的策略，使用真实 AI 验证策略是否被正确实现。

### 策略覆盖

| 策略 | 描述 | 场景数 |
|------|------|--------|
| field_collection | 字段分级与收集顺序 | 38 |
| first_turn | 首轮体验（承接优先） | 14 |
| humanlike | 拟人化承接与转场 | 28 |
| faq | FAQ 处理 | 19 |
| contact | 联系方式触发 | 41 |
| ending | 收尾处理 | 17 |
| robustness | 鲁棒性与安全 | 15 |
| matchmaker | 红娘咨询边界 | 29 |

### 运行命令

```bash
# 列出所有策略和场景
python scripts/run_dialog_policy_regression.py --list

# 运行指定策略（使用真实 AI）
python scripts/run_dialog_policy_regression.py --policy contact
python scripts/run_dialog_policy_regression.py --policy faq
python scripts/run_dialog_policy_regression.py --policy humanlike

# 运行全部策略
python scripts/run_dialog_policy_regression.py --policy all --verbose

# 遇到失败就停止
python scripts/run_dialog_policy_regression.py --policy contact --stop-on-failure
```

### 两种模式对比

| 模式 | FakeAI | 真实 AI（--real-ai） |
|------|--------|---------------------|
| 速度 | 快 | 慢（3-10秒/轮） |
| 网络需求 | 不需要 | 需要联网 |
| Token 消耗 | 0 | 消耗 token |
| 适用场景 | CI/CD、逻辑验证 | 验证实际对话效果 |
