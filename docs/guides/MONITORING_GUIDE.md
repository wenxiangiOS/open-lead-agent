# 监控系统使用指南

本文档介绍 Doubao MCP Server 的监控系统，包括指标收集、健康检查和告警功能。

## 目录

- [概述](#概述)
- [指标收集](#指标收集)
- [健康检查](#健康检查)
- [告警系统](#告警系统)
- [最佳实践](#最佳实践)

---

## 概述

监控系统提供三大核心功能：

1. **指标收集** - 记录各种业务和系统指标
2. **健康检查** - 监控系统和服务健康状态
3. **告警系统** - 基于规则的告警和多渠道通知

### 核心组件

```
src/monitoring/
├── metrics.py    # 指标收集器
├── health.py     # 健康检查
├── alerting.py   # 告警系统
└── __init__.py   # 模块导出
```

---

## 指标收集

### Counter 计数器

只增不减的数值，用于记录事件发生次数。

```python
from src.monitoring import counter

# 创建计数器
requests_total = counter(
    "api_requests_total",
    "API 总请求数",
    labels=["method", "endpoint"]  # 可选的标签维度
)

# 增加计数（默认 +1）
requests_total.inc()

# 增加指定值
requests_total.inc(5)

# 带标签增加
requests_total.inc(labels={"method": "GET", "endpoint": "/api/users"})

# 获取当前值
value = requests_total.get_value()

# 获取所有标签组合的值
all_values = requests_total.get_all_values()
```

### Gauge 仪表盘

可以增减的数值，用于记录当前状态。

```python
from src.monitoring import gauge

# 创建仪表盘
active_connections = gauge(
    "active_connections",
    "活跃连接数"
)

# 设置值
active_connections.set(10)

# 增加值
active_connections.inc(5)

# 减少值
active_connections.dec(2)

# 获取当前值
current = active_connections.get_value()
```

### Histogram 直方图

记录值的分布情况，用于统计响应时间等。

```python
from src.monitoring import histogram

# 创建直方图
request_duration = histogram(
    "request_duration_seconds",
    "请求耗时（秒）",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]  # 可选，自定义桶
)

# 观察一个值
request_duration.observe(0.123)

# 获取统计信息
stats = request_duration.get_value()
# stats = {
#     "count": 100,      # 总观察次数
#     "sum": 12.5,       # 总和
#     "buckets": {       # 桶统计
#         "0.01": 10,
#         "0.05": 50,
#         ...
#     }
# }
```

### Summary 摘要

记录值的分位数统计。

```python
from src.monitoring import summary

# 创建摘要
response_size = summary(
    "response_size_bytes",
    "响应大小（字节）"
)

# 观察值
response_size.observe(1024)
response_size.observe(2048)

# 获取统计
stats = response_size.get_value()
# stats = {
#     "count": 2,
#     "sum": 3072,
#     "quantiles": {
#         "0.5": 2048,   # P50
#         "0.9": 2048,   # P90
#         "0.95": 2048,  # P95
#         "0.99": 2048   # P99
#     }
# }
```

---

## 健康检查

### 基本使用

```python
from src.monitoring import HealthCheckManager, HealthStatus

# 创建健康检查管理器
health_manager = HealthCheckManager()

# 注册健康检查
async def check_database() -> bool:
    # 检查数据库连接
    return database.is_connected()

health_manager.register("database", check_database, critical=True)

# 执行单个检查
result = await health_manager.check("database")
print(f"状态: {result.status}")
print(f"消息: {result.message}")

# 执行所有检查
all_results = await health_manager.check_all()

# 获取整体健康状态
status = await health_manager.get_health_status()
# status = {
#     "status": "healthy",
#     "unhealthy_count": 0,
#     "degraded_count": 0,
#     "total_checks": 5,
#     "checks": {...}
# }
```

### 预定义检查函数

```python
from src.monitoring import (
    create_database_check,
    create_redis_check,
    create_http_check,
    create_disk_space_check,
    create_memory_check
)

# 数据库检查
health_manager.register(
    "database",
    create_database_check(lambda: get_db_connection())
)

# Redis 检查
health_manager.register(
    "redis",
    create_redis_check(redis_client)
)

# HTTP 检查
health_manager.register(
    "external_api",
    create_http_check("https://api.example.com/health")
)

# 磁盘空间检查
health_manager.register(
    "disk_space",
    create_disk_space_check("/", threshold_mb=1000)
)

# 内存使用检查
health_manager.register(
    "memory",
    create_memory_check(threshold_percent=90)
)
```

### 自定义检查

```python
async def custom_check() -> tuple:
    """返回状态和消息"""
    try:
        # 执行检查逻辑
        result = await some_check_function()
        
        if result:
            return (HealthStatus.HEALTHY, "检查通过")
        else:
            return (HealthStatus.UNHEALTHY, "检查失败")
            
    except Exception as e:
        return (HealthStatus.UNKNOWN, f"检查异常: {e}")

health_manager.register("custom", custom_check)
```

---

## 告警系统

### 基本使用

```python
from src.monitoring import AlertManager, AlertSeverity

# 创建告警管理器
alert_manager = AlertManager()

# 创建阈值规则
from src.monitoring import create_threshold_rule

error_rate_rule = create_threshold_rule(
    name="high_error_rate",
    metric_value_getter=lambda: get_current_error_rate(),
    threshold=0.05,  # 5%
    operator="gt",   # 大于
    severity=AlertSeverity.ERROR
)

alert_manager.add_rule(error_rate_rule)

# 评估规则（通常在定时任务中）
alerts = await alert_manager.evaluate_rules()

for alert in alerts:
    print(f"告警: {alert.name} - {alert.message}")
```

### 自定义告警规则

```python
from src.monitoring import AlertRule, AlertSeverity

# 自定义条件函数
def check_condition(**kwargs) -> bool:
    # 自定义检查逻辑
    cpu_usage = kwargs.get("cpu_usage", 0)
    memory_usage = kwargs.get("memory_usage", 0)
    
    return cpu_usage > 80 or memory_usage > 90

# 创建规则
rule = AlertRule(
    name="resource_alert",
    condition=check_condition,
    severity=AlertSeverity.WARNING,
    message_template="资源使用过高: CPU {cpu_usage}%, 内存 {memory_usage}%",
    cooldown=60  # 冷却时间（秒）
)

alert_manager.add_rule(rule)

# 评估时传入参数
alerts = await alert_manager.evaluate_rules(
    cpu_usage=85,
    memory_usage=75
)
```

### 通知渠道

#### 日志通知（默认）

```python
from src.monitoring import LogAlertChannel

# 默认已添加，无需额外配置
```

#### Webhook 通知

```python
from src.monitoring import WebhookAlertChannel

webhook = WebhookAlertChannel(
    name="slack",
    url="https://hooks.slack.com/services/...",
    headers={"Content-Type": "application/json"}
)

alert_manager.add_channel(webhook)
```

#### 邮件通知

```python
from src.monitoring import EmailAlertChannel

email = EmailAlertChannel(
    name="email",
    smtp_host="smtp.example.com",
    smtp_port=587,
    username="user@example.com",
    password="password",
    from_addr="alerts@example.com",
    to_addrs=["admin@example.com", "ops@example.com"]
)

alert_manager.add_channel(email)
```

---

## 最佳实践

### 1. 指标命名

使用描述性的名称，遵循命名规范：

```python
# ✅ 推荐
api_requests_total
api_request_duration_seconds
db_connections_active

# ❌ 不推荐
requests
duration
conns
```

### 2. 标签使用

标签用于创建多维度指标：

```python
# 使用标签区分不同维度
request_counter = counter(
    "api_requests_total",
    "API 总请求数",
    labels=["method", "endpoint", "status"]
)

# 记录时指定标签
request_counter.inc(labels={
    "method": "GET",
    "endpoint": "/api/users",
    "status": "success"
})
```

### 3. 直方图桶选择

根据业务特点选择合适的桶边界：

```python
# 快速响应的 API
fast_api = histogram(
    "fast_api_duration",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

# 慢速的后台任务
slow_task = histogram(
    "slow_task_duration",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)
```

### 4. 健康检查分级

区分关键和非关键检查：

```python
# 关键检查 - 失败会导致整体不健康
health_manager.register("database", check_db, critical=True)

# 非关键检查 - 失败不影响整体状态
health_manager.register("cache", check_cache, critical=False)
```

### 5. 告警规则设计

合理设置阈值和冷却时间：

```python
# 避免告警风暴
rule = AlertRule(
    name="important_alert",
    condition=check_func,
    cooldown=300,  # 5分钟冷却时间
    severity=AlertSeverity.ERROR
)
```

---

## 完整示例

```python
import asyncio
from src.monitoring import (
    counter, histogram, gauge,
    HealthCheckManager,
    AlertManager, AlertSeverity, create_threshold_rule
)

class ServiceMonitor:
    """服务监控示例"""
    
    def __init__(self):
        # 创建指标
        self.requests = counter("requests_total", "总请求数")
        self.latency = histogram("latency_seconds", "请求延迟")
        self.connections = gauge("connections", "活跃连接")
        
        # 创建健康检查管理器
        self.health = HealthCheckManager()
        
        # 创建告警管理器
        self.alerts = AlertManager()
        
        # 设置告警规则
        self.alerts.add_rule(create_threshold_rule(
            "high_latency",
            lambda: self.get_avg_latency(),
            threshold=1.0,
            severity=AlertSeverity.WARNING
        ))
    
    def record_request(self, duration: float):
        """记录请求"""
        self.requests.inc()
        self.latency.observe(duration)
        self.connections.inc()
    
    def record_response(self):
        """记录响应"""
        self.connections.dec()
    
    def get_avg_latency(self) -> float:
        """获取平均延迟"""
        stats = self.latency.get_value()
        if stats["count"] == 0:
            return 0
        return stats["sum"] / stats["count"]
    
    async def check_health(self):
        """检查健康状态"""
        return await self.health.get_health_status()
    
    async def evaluate_alerts(self):
        """评估告警"""
        return await self.alerts.evaluate_rules()

# 使用示例
async def main():
    monitor = ServiceMonitor()
    
    # 模拟请求
    monitor.record_request(0.1)
    monitor.record_response()
    
    # 检查健康
    health = await monitor.check_health()
    print(f"健康状态: {health['status']}")
    
    # 评估告警
    alerts = await monitor.evaluate_alerts()
    for alert in alerts:
        print(f"告警: {alert.message}")

asyncio.run(main())
```

更多示例请参考 `examples/monitoring_example.py`。
