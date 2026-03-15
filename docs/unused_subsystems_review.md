# 未接入子系统评审记录

更新时间：2026-03-14

## 结论摘要

当前项目主链路集中在：

- `src/api/`
- `src/services/`
- `src/models/`
- `src/config/`
- `src/utils/validators.py`

以下子系统目前看起来都**没有接入当前主业务运行链路**，但代码完整度较高，更像历史扩展层或未来预留层，而不是单纯垃圾代码：

- `src/database/`
- `src/monitoring/`
- `src/plugins/`
- `plugins/`

建议处理原则：

- 短期：保留，不直接删除
- 中期：如确认不用，可整体归档
- 不建议：在未做专项验证前直接删除

---

## 1. database 子系统

目录：

- `src/database/__init__.py`
- `src/database/connection.py`
- `src/database/models.py`
- `src/database/repositories.py`
- `src/database/migrations.py`

### 当前判断

- 具备完整数据库抽象层设计
- 包含连接、模型、仓库、迁移
- 代码并非草稿，结构完整
- 但当前主业务链路没有实际走这套

### 当前主链路实际方案

当前用户状态和用户资料主要还是通过以下链路管理：

- `src/services/data/user_service.py`
- `src/services/data/redis_service.py`

### 结论

- 状态：未接入
- 性质：历史持久化方案/未来 SQL 持久化预留
- 建议：保留，列为归档候选

---

## 2. monitoring 子系统

目录：

- `src/monitoring/__init__.py`
- `src/monitoring/metrics.py`
- `src/monitoring/health.py`
- `src/monitoring/alerting.py`

### 当前判断

- 指标、健康检查、告警系统都实现得比较完整
- 具备独立能力，不是半成品
- 但当前 app 启动链路、核心 service、中间件没有真正接入这套监控框架

### 结论

- 状态：未接入
- 性质：监控扩展层/未来建设预留
- 建议：保留，列为归档候选

---

## 3. plugins 子系统

目录：

- `src/plugins/__init__.py`
- `src/plugins/base.py`
- `src/plugins/hooks.py`
- `src/plugins/manager.py`
- `plugins/builtin/logging_plugin.py`
- `plugins/builtin/cache_plugin.py`
- `plugins/builtin/analytics_plugin.py`

### 当前判断

- 插件框架完整，包含基类、管理器、钩子系统
- 内置插件也不是空壳
- 但当前应用启动链路没有加载插件系统
- 也没有自动注册 builtin 插件

### 结论

- 状态：未接入
- 性质：插件扩展层/未来扩展预留
- 建议：保留，列为归档候选

---

## 4. 后续建议

如果后续目标是继续瘦身项目，可以按以下顺序推进：

1. 先确认未来 3-6 个月内是否会启用 SQL 持久化、监控系统、插件系统
2. 如果不会启用，则将这些目录整体迁移到 `archive/`
3. 归档后再更新文档和导入路径说明
4. 不建议在没有专项验证的情况下直接删除整块子系统

---

## 5. 当前建议动作

当前推荐：

- 保留这几块代码
- 不纳入当前主链路改造范围
- 文档中明确标记为“未接入子系统”

当前不推荐：

- 直接删除 `src/database/`
- 直接删除 `src/monitoring/`
- 直接删除 `src/plugins/` 和 `plugins/`
