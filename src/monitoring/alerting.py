"""
告警系统

提供告警规则引擎、检测和通知功能
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 告警级别
# ============================================================================

class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重


# ============================================================================
# 告警状态
# ============================================================================

class AlertStatus(Enum):
    """告警状态"""
    FIRING = "firing"       # 触发中
    RESOLVED = "resolved"   # 已解决
    ACKED = "acked"         # 已确认


# ============================================================================
# 告警事件
# ============================================================================

@dataclass
class Alert:
    """
    告警事件

    Attributes:
        name: 告警名称
        severity: 告警级别
        status: 告警状态
        message: 告警消息
        details: 详细信息
        labels: 标签
        value: 触发值
        threshold: 阈值
        fired_at: 触发时间
        resolved_at: 解决时间
    """
    name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    value: Optional[float] = None
    threshold: Optional[float] = None
    fired_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    acked_by: Optional[str] = None
    acked_at: Optional[float] = None

    def resolve(self):
        """解决告警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = time.time()

    def acknowledge(self, user: str = "system"):
        """确认告警"""
        self.status = AlertStatus.ACKED
        self.acked_by = user
        self.acked_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "labels": self.labels,
            "value": self.value,
            "threshold": self.threshold,
            "fired_at": self.fired_at,
            "resolved_at": self.resolved_at,
            "acked_by": self.acked_by,
            "acked_at": self.acked_at
        }


# ============================================================================
# 告警规则
# ============================================================================

class AlertRule:
    """
    告警规则

    定义何时触发告警
    """

    def __init__(
        self,
        name: str,
        condition: Callable[..., bool],
        severity: AlertSeverity = AlertSeverity.WARNING,
        message_template: str = "{name} 触发告警",
        labels: Dict[str, str] = None,
        cooldown: float = 60.0
    ):
        """
        初始化告警规则

        Args:
            name: 规则名称
            condition: 触发条件函数
            severity: 告警级别
            message_template: 消息模板
            labels: 标签
            cooldown: 冷却时间（秒）
        """
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message_template = message_template
        self.labels = labels or {}
        self.cooldown = cooldown
        self._last_fired = 0
        self._active_alert: Optional[Alert] = None

    def evaluate(self, **kwargs) -> Optional[Alert]:
        """
        评估规则

        Args:
            **kwargs: 传递给条件函数的参数

        Returns:
            如果触发则返回 Alert，否则返回 None
        """
        # 检查冷却时间
        now = time.time()
        if now - self._last_fired < self.cooldown:
            return None

        try:
            # 评估条件
            should_fire = self.condition(**kwargs)

            if should_fire:
                self._last_fired = now

                # 构建消息
                message = self.message_template.format(
                    name=self.name,
                    **kwargs
                )

                # 创建告警
                alert = Alert(
                    name=self.name,
                    severity=self.severity,
                    message=message,
                    labels=self.labels.copy(),
                    details=kwargs
                )

                self._active_alert = alert
                return alert

            elif self._active_alert:
                # 条件不再满足，解决告警
                self._active_alert.resolve()
                resolved = self._active_alert
                self._active_alert = None
                return resolved

        except Exception as e:
            logger.error(f"评估告警规则失败 {self.name}: {e}")

        return None


# ============================================================================
# 告警通知渠道
# ============================================================================

class AlertChannel:
    """
    告警通知渠道

    发送告警通知到各种目的地
    """

    def __init__(self, name: str):
        """初始化通知渠道"""
        self.name = name
        self._enabled = True

    async def send(self, alert: Alert) -> bool:
        """
        发送告警通知

        Args:
            alert: 告警事件

        Returns:
            是否发送成功
        """
        raise NotImplementedError

    def enable(self):
        """启用通知渠道"""
        self._enabled = True

    def disable(self):
        """禁用通知渠道"""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """是否启用"""
        return self._enabled


class LogAlertChannel(AlertChannel):
    """日志通知渠道"""

    def __init__(self, name: str = "log"):
        super().__init__(name)

    async def send(self, alert: Alert) -> bool:
        """记录告警到日志"""
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.warning)

        log_func(
            f"🚨 告警: {alert.name} [{alert.severity.value}] {alert.message}",
            extra={"alert": alert.to_dict()}
        )
        return True


class WebhookAlertChannel(AlertChannel):
    """Webhook 通知渠道"""

    def __init__(
        self,
        name: str,
        url: str,
        headers: Dict[str, str] = None,
        timeout: float = 10.0
    ):
        super().__init__(name)
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        """发送 Webhook"""
        try:
            import httpx

            payload = {
                "alert": alert.to_dict(),
                "timestamp": time.time()
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json=payload,
                    headers=self.headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Webhook 发送失败: {e}")
            return False


class EmailAlertChannel(AlertChannel):
    """邮件通知渠道"""

    def __init__(
        self,
        name: str,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str]
    ):
        super().__init__(name)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    async def send(self, alert: Alert) -> bool:
        """发送邮件"""
        try:
            import smtplib
            from email.mime.text import MIMEText

            # 构建邮件
            subject = f"[{alert.severity.value.upper()}] {alert.name}"
            body = f"""
告警名称: {alert.name}
告警级别: {alert.severity.value}
告警消息: {alert.message}
触发时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.fired_at))}
"""

            if alert.details:
                body += f"\n详细信息:\n{alert.details}\n"

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False


# ============================================================================
# 告警管理器
# ============================================================================

class AlertManager:
    """
    告警管理器

    管理告警规则、检测和通知
    """

    def __init__(self):
        """初始化告警管理器"""
        self._rules: Dict[str, AlertRule] = {}
        self._channels: Dict[str, AlertChannel] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._max_history = 1000

        # 默认添加日志通知渠道
        self.add_channel(LogAlertChannel())

    def add_rule(self, rule: AlertRule):
        """
        添加告警规则

        Args:
            rule: 告警规则
        """
        self._rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name}")

    def remove_rule(self, name: str) -> bool:
        """
        移除告警规则

        Args:
            name: 规则名称

        Returns:
            是否移除成功
        """
        if name in self._rules:
            del self._rules[name]
            if name in self._active_alerts:
                del self._active_alerts[name]
            logger.info(f"移除告警规则: {name}")
            return True
        return False

    def add_channel(self, channel: AlertChannel):
        """
        添加通知渠道

        Args:
            channel: 通知渠道
        """
        self._channels[channel.name] = channel
        logger.info(f"添加通知渠道: {channel.name}")

    def remove_channel(self, name: str) -> bool:
        """
        移除通知渠道

        Args:
            name: 渠道名称

        Returns:
            是否移除成功
        """
        if name in self._channels:
            del self._channels[name]
            logger.info(f"移除通知渠道: {name}")
            return True
        return False

    async def evaluate_rules(self, **kwargs) -> List[Alert]:
        """
        评估所有规则

        Args:
            **kwargs: 传递给规则条件的参数

        Returns:
            触发的告警列表
        """
        alerts = []

        for rule in self._rules.values():
            alert = rule.evaluate(**kwargs)
            if alert:
                alerts.append(alert)

                # 处理告警
                await self._process_alert(alert)

        return alerts

    async def _process_alert(self, alert: Alert):
        """
        处理告警

        Args:
            alert: 告警事件
        """
        # 记录到历史
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        # 更新活跃告警
        if alert.status == AlertStatus.FIRING:
            self._active_alerts[alert.name] = alert
        elif alert.status == AlertStatus.RESOLVED:
            if alert.name in self._active_alerts:
                del self._active_alerts[alert.name]

        # 发送通知
        await self._send_notifications(alert)

    async def _send_notifications(self, alert: Alert):
        """
        发送告警通知

        Args:
            alert: 告警事件
        """
        for channel in self._channels.values():
            if not channel.is_enabled:
                continue

            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(f"发送告警通知失败 ({channel.name}): {e}")

    def get_active_alerts(self) -> List[Alert]:
        """获取所有活跃告警"""
        return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self._alert_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        history = self._alert_history

        return {
            "total_alerts": len(history),
            "active_alerts": len(self._active_alerts),
            "rules_count": len(self._rules),
            "channels_count": len(self._channels),
            "by_severity": {
                severity.value: sum(1 for a in history if a.severity == severity)
                for severity in AlertSeverity
            }
        }


# ============================================================================
# 预定义的告警规则
# ============================================================================

def create_threshold_rule(
    name: str,
    metric_value_getter: Callable[[], float],
    threshold: float,
    operator: str = "gt",
    severity: AlertSeverity = AlertSeverity.WARNING
) -> AlertRule:
    """
    创建阈值告警规则

    Args:
        name: 规则名称
        metric_value_getter: 获取指标值的函数
        threshold: 阈值
        operator: 比较操作符（gt, lt, gte, lte, eq）
        severity: 告警级别

    Returns:
        告警规则
    """
    operators = {
        "gt": lambda x, y: x > y,
        "lt": lambda x, y: x < y,
        "gte": lambda x, y: x >= y,
        "lte": lambda x, y: x <= y,
        "eq": lambda x, y: x == y,
    }

    op_func = operators.get(operator, operators["gt"])

    def condition(**kwargs) -> bool:
        value = metric_value_getter()
        return op_func(value, threshold)

    message_template = f"{{name}} 当前值 {{value}} {operator} 阈值 {threshold}"

    return AlertRule(
        name=name,
        condition=condition,
        severity=severity,
        message_template=message_template
    )


# ============================================================================
# 全局告警管理器
# ============================================================================

# 默认告警管理器
default_alert_manager = AlertManager()
