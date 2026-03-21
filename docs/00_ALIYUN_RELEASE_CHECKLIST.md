# 阿里云发布前流程清单（唯一执行版）

更新时间：2026-03-20  
适用范围：本项目发布到阿里云 ECS（含 Nginx + Gunicorn + Redis）

> 执行原则：必须按顺序走；上一步不通过，不进入下一步。

---

## 0. 发布输入信息（先确认）

- [ ] 发布版本：`<git commit / tag>`
- [ ] 发布窗口：`<日期时间>`
- [ ] 回滚版本：`<上一个稳定 tag>`
- [ ] 发布负责人：`<name>`

---

## 1. 环境与配置准备

- [ ] 阿里云 ECS 规格满足最低要求（建议 4C8G+，SSD）
- [ ] Redis 可用，连接参数正确
- [ ] `.env` 生产参数完整（至少含）：
`ARK_API_KEY`、`MODEL_NAME`、`REDIS_*`、`HOST`、`PORT`、`LOG_LEVEL`
- [ ] 生产域名、HTTPS 证书、Nginx 配置完成
- [ ] 防火墙仅开放必要端口（22/80/443）

---

## 2. 基础健康检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/doubao/mq/dashboard
```

- [ ] `/health` 返回成功
- [ ] `mq/dashboard` 可访问且结构完整

---

## 3. 回归测试（发布前必须全通过）

发布前建议先直接执行这一条总命令，全部通过后再逐项核对下面 3.1/3.2/3.3/3.4：

```bash
bash scripts/run_release_preflight.sh
```

如需覆盖环境参数（例如线上机器地址）：

```bash
BASE_URL=http://127.0.0.1:8000 MQ_ACCOUNTS=20 MQ_MESSAGES_PER_ACCOUNT=10 MQ_CONCURRENCY=20 bash scripts/run_release_preflight.sh
```

### 3.1 质量上限门禁（chat 必跑阻断）

```bash
bash scripts/run_quality_upper_bound_gate.sh
```

- [ ] 金标长链回放通过（`tests/real_ai/scenarios_golden/golden_long_chain_quality.json`）
- [ ] 全覆盖 strict 风险项无阻断
- [ ] 输出包含 `[quality-gate] PASS`

### 3.2 真人仿真回归（抽检，可选但建议）

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```

- [ ] 抽检报告无明显拟人化退化/字段退化

### 3.3 MQ ingest 场景回归（20 场景）

```bash
python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000
```

- [ ] `20/20 PASS`（`0 FAIL`，`0 SKIP`）

### 3.4 MQ 小并发门禁（阻断发布）

```bash
python3 scripts/run_mq_load_test.py \
  --base-url http://127.0.0.1:8000 \
  --accounts 20 \
  --messages-per-account 10 \
  --concurrency 20 \
  --include-dashboard \
  --gate
```

- [ ] 输出 `gate_passed: True`
- [ ] 报告已生成到 `reports/mq_load/`

---

## 4. 生产联调 Smoke（外部通道）

```bash
export XHS_REPLY_API='https://<your-xhs-endpoint>'
python3 scripts/run_mq_p0_production_smoke.py \
  --timeout-seconds 30 \
  --report-file reports/mq/p0_production_smoke_$(date +%Y%m%d_%H%M%S).md
```

- [ ] smoke 报告 PASS
- [ ] 至少 1 条真实 outbox 成功投递

---

## 5. 发布执行（阿里云）

- [ ] 拉取目标版本并安装依赖
- [ ] 重启 Gunicorn / Systemd 服务
- [ ] Nginx reload 成功
- [ ] 发布后 5 分钟内完成健康检查

---

## 6. 发布后首日巡检（必须做）

- [ ] `pending_depth` 无持续攀升
- [ ] `ingest_queue_full` 无异常尖峰
- [ ] `outbox_delivery_success` 持续增长
- [ ] `turn_failed`、`stale_drop_count` 无异常抬升
- [ ] 无用户侧大面积延迟/乱序/丢消息
- [ ] `obs.turn` 日志可检索，且 `ok=0` 占比低于阈值
- [ ] `route=model` 的 `total_ms` 无持续高位异常

---

## 7. 回滚触发条件（任一命中即回滚）

- [ ] 健康检查持续失败（>5 分钟）
- [ ] 核心接口错误率明显异常
- [ ] 队列积压持续恶化且无法快速回落
- [ ] 外发通道持续失败导致用户不可用

回滚动作：

1. 切回上一个稳定版本
2. 重启服务并验证 `/health`
3. 记录事故时间线与根因

---

## 8. 证据归档（发布完成后）

- [ ] 归档 `run_random_user_simulation` 报告
- [ ] 归档 `run_mq_ingest_regression` 结果
- [ ] 归档 `run_mq_load_test` JSON 报告
- [ ] 归档生产 smoke 报告
- [ ] 执行 `python3 scripts/generate_report_index.py` 并确认 `reports/INDEX.md` 已更新
- [ ] 在发布记录里写明版本、时间、结论

---

## 参考文档

- `docs/guides/DEPLOYMENT_GUIDE.md`
- `docs/message_queue_runbook.md`
- `docs/01_ALIYUN_OBS_ALERT_PLAYBOOK.md`
- `docs/02_ALIYUN_SLS_ALERT_SETUP.md`
- `tests/real_ai/README.md`
