"""
监控系统

提供指标收集、健康检查和告警功能
"""

from .metrics import (
    Metric,
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricRegistry,
    default_registry,
    counter,
    gauge,
    histogram,
    summary
)

from .health import (
    HealthStatus,
    HealthCheckResult,
    HealthChecker,
    HealthCheckManager,
    create_database_check,
    create_redis_check,
    create_http_check,
    create_disk_space_check,
    create_memory_check,
    default_health_manager
)

from .alerting import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertRule,
    AlertChannel,
    LogAlertChannel,
    WebhookAlertChannel,
    EmailAlertChannel,
    AlertManager,
    create_threshold_rule,
    default_alert_manager
)

__all__ = [
    # 指标
    'Metric',
    'Counter',
    'Gauge',
    'Histogram',
    'Summary',
    'MetricRegistry',
    'default_registry',
    'counter',
    'gauge',
    'histogram',
    'summary',

    # 健康检查
    'HealthStatus',
    'HealthCheckResult',
    'HealthChecker',
    'HealthCheckManager',
    'create_database_check',
    'create_redis_check',
    'create_http_check',
    'create_disk_space_check',
    'create_memory_check',
    'default_health_manager',

    # 告警
    'Alert',
    'AlertSeverity',
    'AlertStatus',
    'AlertRule',
    'AlertChannel',
    'LogAlertChannel',
    'WebhookAlertChannel',
    'EmailAlertChannel',
    'AlertManager',
    'create_threshold_rule',
    'default_alert_manager',
]
