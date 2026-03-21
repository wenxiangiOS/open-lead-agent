# 阿里云 SLS 告警规则配置清单（逐步操作版）

更新时间：2026-03-21
适用：`obs.turn` 日志已接入 SLS 的项目

## 1. 先决条件
- 已创建 SLS Project 和 Logstore。
- 应用日志已写入 SLS。
- 可检索到关键字：`[obs.turn]`。
- 已准备告警通知渠道（钉钉/飞书/企微 Webhook）。

## 2. 控制台基础操作路径
1. 进入阿里云日志服务 SLS 控制台。
2. 选择对应 Project -> Logstore。
3. 在“查询分析”中先验证：
   - 查询：`"[obs.turn]"`
   - 能返回近 5 分钟日志。
4. 打开“告警” -> “创建告警规则”。

## 3. 推荐规则（按优先级）

### 3.1 P1：错误率告警（5 分钟 > 2%）
- 名称：`chat_obs_turn_error_rate_p1`
- 查询窗口：5 分钟
- 查询语句：

```text
"[obs.turn]"
```

- 聚合方式：
  - 总请求数：`count(*)`
  - 失败数：过滤 `ok=0` 后 `count(*)`
  - 错误率：`failed / total`
- 阈值：`> 0.02`
- 触发持续：连续 2 个周期
- 通知：钉钉/飞书 + 电话（值班）

> 说明：如果控制台不方便直接做分子分母，可先做“失败次数 > N”告警，再补错误率规则。

### 3.2 P1：模型主路由延迟告警（P95 > 8000ms）
- 名称：`chat_model_route_latency_p95_p1`
- 查询窗口：5 分钟
- 查询语句：

```text
"[obs.turn]" and "route=model"
```

- 指标：`total_ms` 的 P95
- 阈值：`> 8000`
- 触发持续：连续 2 个周期
- 通知：钉钉/飞书

### 3.3 P1：AI 硬超时突增告警
- 名称：`chat_ai_hard_timeout_spike_p1`
- 查询窗口：3 分钟
- 查询语句：

```text
"总时长触发硬超时"
```

- 指标：`count(*)`
- 阈值：按基线设置（建议初期 `>= 10/3min`）
- 通知：钉钉/飞书 + 电话

### 3.4 P2：抽取空字段异常告警
- 名称：`chat_extracted_fields_zero_ratio_p2`
- 查询窗口：10 分钟
- 查询语句：

```text
"[obs.turn]" and "route=model"
```

- 指标：`extracted_fields=0` 占比
- 阈值：高于最近 7 天基线 + 15%
- 通知：钉钉/飞书

### 3.5 P2：Prompt 体积异常告警
- 名称：`chat_prompt_chars_spike_p2`
- 查询窗口：10 分钟
- 查询语句：

```text
"[obs.turn]" and "route=model"
```

- 指标：`prompt_chars` P95
- 阈值：`> 9000`（按你业务可调）
- 通知：钉钉/飞书

## 4. 告警抑制与降噪建议
- 同类告警静默时间：10 分钟。
- 夜间保留 P1 电话，P2 仅 IM。
- 同时命中“错误率+延迟”时，合并推送为一条升级告警。

## 5. 告警消息模板（建议）

```text
[聊天服务告警]
规则: ${alert_name}
时间: ${alert_time}
项目: ${project}/${logstore}
当前值: ${current_value}
阈值: ${threshold}
建议动作: 1) 查 obs.turn 2) 按 trace_id 回放 3) 评估回滚
```

## 6. 值班排查 SOP（收到告警后）
1. 先看最近 5 分钟 `obs.turn` 总量和失败量。
2. 若错误率高：优先查 `ok=0` + `error` 字段。
3. 若延迟高：查 `route=model` 的 `prompt_chars` 和 `stages`。
4. 抽样 3 条失败日志，按 `trace_id` 完整回放链路。
5. 10 分钟内无法收敛，执行降级：
   - 关闭快模型路由。
   - 下调 `CHAT_AI_MAX_TOKENS`。
   - 必要时切旧 Prompt 版本。

## 7. 发布门禁联动（建议）
- 发版后 30 分钟观察窗：
  - 错误率 <= 2%
  - `route=model` P95 <= 8000ms
  - 无超时突增告警
- 任一失败，不允许继续从 10% 灰度升到 50%。

## 8. 关联文档
- `docs/01_ALIYUN_OBS_ALERT_PLAYBOOK.md`
- `docs/00_ALIYUN_RELEASE_CHECKLIST.md`
- `docs/prompt_optimization_final_plan.md`
