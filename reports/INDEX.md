# 报告索引（自动生成）

更新时间：`2026-03-21 11:01:32`

使用说明：
- 每次跑完回归后执行：`python3 scripts/generate_report_index.py`
- 统一从本文件查看各类报告最新路径，避免忘记目录。

## 真实用户仿真回归
- 目录：`reports/real_ai_realism`
- 最新报告：`reports/real_ai_realism/latest.md`
- 更新时间：`2026-03-21 10:10:45`
- 报告总数：`64`
- 生成命令：`python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose`

最近 5 份：
- `reports/real_ai_realism/latest.md` (2026-03-21 10:10:45)
- `reports/real_ai_realism/realism_regression_20260321_101045.md` (2026-03-21 10:10:45)
- `reports/real_ai_realism/latest.json` (2026-03-21 10:10:45)
- `reports/real_ai_realism/realism_regression_20260321_101045.json` (2026-03-21 10:10:45)
- `reports/real_ai_realism/realism_regression_20260321_033743.md` (2026-03-21 03:37:43)

## Chat 回归
- 目录：`reports/real_ai`
- 最新报告：`reports/real_ai/latest.md`
- 更新时间：`2026-03-19 16:50:31`
- 报告总数：`18`
- 生成命令：`python3 scripts/run_real_ai_regression.py`

最近 5 份：
- `reports/real_ai/latest.md` (2026-03-19 16:50:31)
- `reports/real_ai/real_ai_regression_20260319_165031.md` (2026-03-19 16:50:31)
- `reports/real_ai/latest.json` (2026-03-19 16:50:31)
- `reports/real_ai/real_ai_regression_20260319_165031.json` (2026-03-19 16:50:31)
- `reports/real_ai/real_ai_regression_20260319_155748.md` (2026-03-19 15:57:48)

## MQ 负载回归
- 目录：`reports/mq_load`
- 最新报告：`reports/mq_load/mq_load_20260320_111309.json`
- 更新时间：`2026-03-20 11:13:09`
- 报告总数：`3`
- 生成命令：`python3 scripts/run_mq_load_test.py --base-url http://127.0.0.1:8000 --accounts 20 --messages-per-account 10 --concurrency 20 --include-dashboard --gate`

最近 5 份：
- `reports/mq_load/mq_load_20260320_111309.json` (2026-03-20 11:13:09)
- `reports/mq_load/mq_load_20260320_111037.json` (2026-03-20 11:10:37)
- `reports/mq_load/mq_load_20260320_111007.json` (2026-03-20 11:10:07)

## MQ 生产 smoke
- 目录：`reports/mq`
- 最新报告：`reports/mq/p0_latency_execution_20260318.md`
- 更新时间：`2026-03-18 19:13:46`
- 报告总数：`7`
- 生成命令：`python3 scripts/run_mq_p0_production_smoke.py --timeout-seconds 30 --report-file reports/mq/p0_production_smoke_$(date +%Y%m%d_%H%M%S).md`

最近 5 份：
- `reports/mq/p0_latency_execution_20260318.md` (2026-03-18 19:13:46)
- `reports/mq/p0_production_smoke_20260318_123638.md` (2026-03-18 12:36:39)
- `reports/mq/p0_acceptance_20260318.md` (2026-03-18 12:36:18)
- `reports/mq/p0_production_smoke_local.md` (2026-03-18 12:36:06)
- `reports/mq/p2_acceptance_20260318.md` (2026-03-18 12:28:31)
