"""
错误严重性定义

将错误按严重程度分级，便于采取不同的处理策略
"""

from enum import IntEnum
from typing import Set


class ErrorSeverity(IntEnum):
    """
    错误严重性等级

    数值越小表示越严重
    """
    CRITICAL = 1   # 系统级错误，需要立即处理
    HIGH = 2       # 功能受损，需要尽快处理
    MEDIUM = 3     # 部分功能受影响
    LOW = 4        # 不影响核心功能

    @classmethod
    def get_recovery_actions(cls, severity: 'ErrorSeverity') -> Set[str]:
        """获取对应的恢复动作"""
        actions = {
            cls.CRITICAL: {
                "alert_team", "trigger_circuit_breaker", "graceful_shutdown"
            },
            cls.HIGH: {
                "alert_team", "trigger_circuit_breaker", "log_detailed"
            },
            cls.MEDIUM: {
                "log_detailed", "attempt_retry", "fallback_strategy"
            },
            cls.LOW: {
                "log_basic", "continue_operation"
            }
        }
        return actions.get(severity, set())

    @classmethod
    def should_alert(cls, severity: 'ErrorSeverity') -> bool:
        """是否需要发送告警"""
        return severity in [cls.CRITICAL, cls.HIGH]

    @classmethod
    def should_retry(cls, severity: 'ErrorSeverity') -> bool:
        """是否可以重试"""
        return severity in [cls.MEDIUM, cls.LOW]

    @classmethod
    def should_fallback(cls, severity: 'ErrorSeverity') -> bool:
        """是否可以降级处理"""
        return severity in [cls.HIGH, cls.MEDIUM]
