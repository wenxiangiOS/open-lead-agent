# 报告索引自动化（阿里云）

更新时间：2026-03-21

## 1. 目标
- 每天自动刷新 `reports/INDEX.md`。
- 你只看一个文件就能知道最新报告位置。

## 2. 手动刷新（随时可用）

```bash
cd /Users/eric/Desktop/doubao_mcp_server
python3 scripts/generate_report_index.py
```

## 3. 定时任务（推荐）

在 ECS 上执行：

```bash
crontab -e
```

加入一行（每天 09:05 自动刷新）：

```bash
5 9 * * * cd /Users/eric/Desktop/doubao_mcp_server && /usr/bin/python3 scripts/generate_report_index.py >> /Users/eric/Desktop/doubao_mcp_server/reports/index_cron.log 2>&1
```

## 4. 验证是否生效
- 查看 `reports/INDEX.md` 顶部更新时间是否变化。
- 查看日志：`reports/index_cron.log`。

## 5. 推荐配套
- 发布前执行：`bash scripts/run_release_preflight.sh`。
- 发布后巡检直接看：`reports/INDEX.md`。
