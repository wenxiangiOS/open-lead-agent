# 阿里云观测与告警配置手册（obs.turn 专用）

更新时间：2026-03-21

## 1. 目标
- 用统一日志 `obs.turn` 快速定位线上问题。
- 把“慢、错、空、失败”转成可告警指标。
- 发布前后都能用同一套查询模板。

## 2. 日志格式（已在代码中落地）
示例：

```text
[obs.turn] trace_id=... account_id=... dialog_id=... ok=1 route=model response_channel=model prompt_chars=3835 extracted_fields=0 total_ms=234 stages=profile_load:2,... error=-
```

关键字段：
- `trace_id`
- `account_id`
- `dialog_id`
- `ok`（1 成功 / 0 失败）
- `route`
- `response_channel`
- `prompt_chars`
- `extracted_fields`
- `total_ms`
- `stages`
- `error`

## 3. SLS 查询模板（直接可用）

说明：以下先用“关键词查询”即可，不依赖结构化解析。

### 3.1 失败请求
```text
"[obs.turn]" and "ok=0"
```

### 3.2 慢请求（总耗时 > 8s）
```text
"[obs.turn]" and "total_ms=" and not "total_ms=0" and not "total_ms=1" and not "total_ms=2" and not "total_ms=3" and not "total_ms=4" and not "total_ms=5" and not "total_ms=6" and not "total_ms=7"
```

### 3.3 AI 主路由健康
```text
"[obs.turn]" and "route=model"
```

### 3.4 风险护栏命中
```text
"[obs.turn]" and ("route=risk_guard" or "route=boundary_pause")
```

### 3.5 快路径命中（FAQ/规则短路）
```text
"[obs.turn]" and ("route=quick_faq" or "route=rule_profile_fast_path" or "route=collection_short_circuit")
```

### 3.6 长 Prompt 监控（排查时延）
```text
"[obs.turn]" and "prompt_chars=" and "route=model"
```

> 实操建议：先点开单条日志，复制 `trace_id` 再二次查询。

### 3.7 按 trace_id 串联单请求
```text
"[obs.turn]" and "trace_id=<你的trace_id>"
```

## 4. 告警规则建议（首版阈值）

### 4.1 错误率告警（P1）
- 条件：5 分钟内 `ok=0` 占比 > 2%
- 动作：钉钉/飞书 + 电话

### 4.2 延迟告警（P1）
- 条件：5 分钟内 `route=model` 的 P95 `total_ms` > 8000
- 动作：钉钉/飞书

### 4.3 超时/降级告警（P1）
- 条件：日志出现 `AI调用` 硬超时关键词连续 3 分钟增长
- 动作：钉钉/飞书 + 自动触发“快路径降级开关”评估

### 4.4 空回复告警（P2）
- 条件：10 分钟内 `response` 为空相关计数明显抬升（结合业务日志）
- 动作：钉钉/飞书

### 4.5 抽取异常告警（P2）
- 条件：`extracted_fields=0` 在 `route=model` 中占比异常升高（按你的基线 +15%）
- 动作：钉钉/飞书

## 5. 上线后排查流程（固定顺序）
1. 看告警面板：先确认是错误率、时延还是抽取异常。
2. 拉最近 5 分钟 `obs.turn`，按 `route` 分组看异常集中点。
3. 抽样失败日志，用 `trace_id` 串联单请求。
4. 检查 `prompt_chars` 是否异常膨胀。
5. 检查 `response_channel` 是否误路由。
6. 检查 `stages` 中哪段耗时异常（如 `ai_call`/`prompt_build`）。

## 6. 应急动作
- 动作A：切回旧 Prompt 版本。
- 动作B：关闭快模型路由（强制主模型）。
- 动作C：下调 `CHAT_AI_MAX_TOKENS`（如 420 -> 320）。
- 动作D：紧急降级到固定模板路径（短时兜底）。

## 7. 建议的初始环境变量
- `AI_ROUTING_ENABLED=true`
- `CHAT_AI_MAX_TOKENS=420`
- `CHAT_AI_LOW_COMPLEXITY_MAX_TOKENS=260`
- `CHAT_AI_HIGH_RISK_MAX_TOKENS=180`
- `CHAT_AI_LONG_PROMPT_CHAR_THRESHOLD=6500`
- `CHAT_AI_LONG_PROMPT_MAX_TOKENS=220`
- `CHAT_AI_TIMEOUT_SECONDS=18`
- `CHAT_AI_HARD_TIMEOUT_SECONDS=22`

## 8. 发布门禁（建议）
发布前 30 分钟观察窗口，以下任一失败不允许全量：
- `ok=0` 占比 > 2%
- `route=model` P95 `total_ms` > 8000
- 空回复或抽取异常连续抬升

## 9. 关联文档
- `docs/prompt_optimization_final_plan.md`
- `docs/00_ALIYUN_RELEASE_CHECKLIST.md`
- `docs/message_queue_runbook.md`
- `reports/INDEX.md`（由 `python3 scripts/generate_report_index.py` 生成）
