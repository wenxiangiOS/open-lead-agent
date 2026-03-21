# 阿里云发布执行记录模板（每次发布复制一份）

建议命名：`docs/release_records/RELEASE_<YYYYMMDD_HHMM>_<version>.md`

---

## 1. 基本信息

- 发布版本（commit/tag）：
- 上一稳定版本（回滚目标）：
- 发布环境：阿里云 ECS
- 发布负责人：
- 开始时间：
- 完成时间：

---

## 2. 发布前检查结果（按流程打勾）

- [ ] 已按 `docs/00_ALIYUN_RELEASE_CHECKLIST.md` 全流程执行
- [ ] 环境与配置检查通过
- [ ] 健康检查通过

### 2.1 质量上限门禁（必填）

命令：

```bash
bash scripts/run_release_preflight.sh
```

结果：

- 预检脚本通过（Y/N）：
- 输出包含 `[preflight] PASS`（Y/N）：
- 报告路径：

### 2.2 Chat 回归（抽检，可选）

命令：

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```

结果：

- 通过：
- 失败：
- 报告路径：

### 2.3 MQ ingest 回归

命令：

```bash
python3 scripts/run_mq_ingest_regression.py --base-url http://127.0.0.1:8000
```

结果：

- 总场景：
- 通过：
- 失败：

### 2.4 MQ 门禁压测

命令：

```bash
python3 scripts/run_mq_load_test.py \
  --base-url http://127.0.0.1:8000 \
  --accounts 20 \
  --messages-per-account 10 \
  --concurrency 20 \
  --include-dashboard \
  --gate
```

结果：

- gate_passed：
- p95/p99：
- rps：
- 报告路径：

### 2.5 生产联调 smoke（如适用）

命令：

```bash
python3 scripts/run_mq_p0_production_smoke.py --timeout-seconds 30 --report-file <path>
```

结果：

- PASS/FAIL：
- 报告路径：

---

## 3. 发布执行记录

- [ ] 已拉取目标版本并安装依赖
- [ ] 已重启 Gunicorn / Systemd
- [ ] 已 reload Nginx
- [ ] 发布后健康检查通过

关键日志/命令输出摘要：

```text
<粘贴核心日志摘要>
```

---

## 4. 发布后 1 小时观察

- `pending_depth`：
- `ingest_queue_full`：
- `outbox_delivery_success`：
- `turn_failed`：
- 用户侧异常反馈：

结论：

- [ ] 正常，无需处理
- [ ] 有异常，已跟进

---

## 5. 回滚记录（仅异常时填写）

- 是否触发回滚：是 / 否
- 触发时间：
- 触发原因：
- 回滚到版本：
- 回滚后验证结果：

---

## 6. 最终结论

- 发布结论：通过 / 未通过
- 后续行动项：

1.
2.
3.
