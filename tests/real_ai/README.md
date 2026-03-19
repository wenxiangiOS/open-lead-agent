# 真实 AI 场景回归

这套测试用于跑真实 `AIService + ChatService` 端到端链路，不 mock 模型回复。

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

推荐首选（真实性仿真）：要看每条用户和 AI 内容，加 --verbose

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42
```

134 全覆盖建议执行顺序：

1. chat 真实性回归（114）：  
`python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42`
2. mq 链路回归（20）：  
`python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000`

随机真人风格批量模拟（抽检）：

```bash
python3 scripts/run_random_user_simulation.py --sessions 20 --min-turns 6 --max-turns 12 --seed 42
```

覆盖场景模式（按场景逐个模拟真人式聊天，默认跳过 mq）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --max-scenarios 114 --seed 42
```

完整覆盖（按场景逐个模拟，输出时延异常与模板化风险）：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42
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
