> 归档说明：本文件已归档，反映的是 2026-03-14 左右的项目结构判断，不代表当前最新现状。
> 当前项目状态请优先参考：`docs/project_status_summary.md`、`docs/refactor_execution_plans.md`、`docs/compat_cleanup_plan.md`

# 项目结构说明

更新时间：2026-03-14

## 顶层结构

```text
doubao_mcp_server/
  src/              # 主代码
  tests/            # 测试
  docs/             # 文档
  scripts/          # 脚本实现
  plugins/          # 内置插件实现（当前未接入）
  test_page/        # 测试页面模块（可选）
  main.py           # 本地启动入口
  testChat.py       # 交互式手工测试工具
  t                 # testChat 快捷入口
  start-redis.sh    # Redis 启动兼容入口
  pytest.ini        # pytest 根配置
```

---

## 主链路

当前主业务链路主要集中在：

- `src/api/`
- `src/services/`
- `src/models/`
- `src/config/`

其中 `src/services/` 已经按职责拆成多层服务，详见：

- `docs/service_boundaries.md`

应用入口：

- `src/api/app.py`

服务启动方式：

- `python3 main.py`
- `bash scripts/start.sh`

---

## API 结构

```text
src/api/
  app.py           # FastAPI app 组装入口
  middleware/      # 中间件
  routes/          # 分模块路由
  v1/              # 兼容层路由
```

说明：

- `src/api/app.py` 负责创建 app、注册 middleware、注入 service、挂载路由
- `src/api/routes/` 负责具体接口定义

---

## 测试结构

见：

- `docs/testing_layout.md`

---

## 手工工具

- `testChat.py`
  交互式聊天测试工具

- `t`
  `testChat.py` 的快捷入口

- `start-redis.sh`
  Redis 启动兼容入口，实际实现位于 `scripts/start-redis.sh`

---

## 服务层现状

当前 `src/services/` 已形成以下主分层：

- `chat_service.py`
  主流程编排层，负责决定调用顺序和最终响应组装

- `core/dialogue_manager.py`
  对话上下文与 prompt 组装层

- `collection/profile_collection_policy.py`
  资料收集策略层

- `collection/contact_collection_service.py`
  联系方式决策层

- `conversation/conversation_ending_service.py`
  收尾场景层

- `data/extraction_service.py`
  提取与落档层

- `data/validation_service.py`
  字段校验层

- `data/user_service.py`
  用户状态与档案存储层

- `conversation/greeting_service.py`
  纯问候识别与开场快捷回复

- `conversation/expectation_service.py`
  匹配时长与预期问答规则

- `conversation/input_fallback_service.py`
  无意义输入、确认词、弱响应兜底

- `collection/ask_tracking_service.py`
  AI 追问字段计数与自动跳过

- `prompts/prompts.py`
  提示词中心与 prompt 构建

---

## 未接入子系统

见：

- `docs/unused_subsystems_review.md`
- `docs/archive_strategy.md`
