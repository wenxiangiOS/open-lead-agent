"""
增强的自定义异常类

所有异常都包含严重性等级和恢复策略
"""

from typing import Optional, Dict, Any, Type
from .error_severity import ErrorSeverity


class EnhancedException(Exception):
    """
    增强的异常基类

    所有自定义异常的父类，包含错误分级、恢复策略、告警配置
    """

    # 默认严重性等级（子类可覆盖）
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    # 是否可重试（子类可覆盖）
    retryable: bool = False

    # 最大重试次数
    max_retries: int = 3

    # 重试延迟（秒）
    retry_delay: float = 1.0

    # 是否需要告警
    requires_alert: bool = False

    # 用户友好的错误消息（子类可覆盖）
    user_message: str = "服务暂时不可用，请稍后重试"

    # 是否应该降级处理
    fallback_available: bool = False

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息（技术描述）
            error_code: 错误代码
            status_code: HTTP 状态码
            details: 错误详情
            context: 错误上下文（用户ID、请求ID等）
            cause: 原始异常（用于异常链）
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.context = context or {}
        self.cause = cause

        # 设置异常链
        if cause:
            self.__cause__ = cause

        super().__init__(self.message)

    @property
    def severity_level(self) -> ErrorSeverity:
        """获取严重性等级"""
        return self.severity

    @property
    def is_retryable(self) -> bool:
        """是否可重试"""
        return self.retryable

    @property
    def should_alert_team(self) -> bool:
        """是否需要告警"""
        return self.requires_alert

    @property
    def has_fallback(self) -> bool:
        """是否有降级方案"""
        return self.fallback_available

    def get_recovery_actions(self) -> set:
        """获取可执行的恢复动作"""
        return ErrorSeverity.get_recovery_actions(self.severity)

    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式

        Args:
            include_debug: 是否包含调试信息（仅开发环境）

        Returns:
            错误信息字典
        """
        result = {
            "error": self.user_message,
            "error_code": self.error_code,
            "details": self.details.copy()
        }

        # 调试模式下包含更多信息
        if include_debug:
            result.update({
                "technical_message": self.message,
                "severity": self.severity.name,
                "retryable": self.retryable,
                "context": self.context
            })

        return result

    def with_context(self, **kwargs) -> 'EnhancedException':
        """添加上下文信息"""
        self.context.update(kwargs)
        return self

    @classmethod
    def from_exception(cls, exc: Exception, **kwargs) -> 'EnhancedException':
        """
        从普通异常创建增强异常

        Args:
            exc: 原始异常
            **kwargs: 额外的参数

        Returns:
            增强异常实例
        """
        return cls(
            message=str(exc),
            details={"original_type": type(exc).__name__},
            cause=exc,
            **kwargs
        )


# ============================================================================
# 具体的异常类型
# ============================================================================

class CriticalException(EnhancedException):
    """系统级严重异常"""
    severity = ErrorSeverity.CRITICAL
    retryable = False
    requires_alert = True
    user_message = "系统严重错误，请稍后重试或联系客服"


class HighSeverityException(EnhancedException):
    """高严重性异常"""
    severity = ErrorSeverity.HIGH
    retryable = True
    max_retries = 2
    retry_delay = 2.0
    requires_alert = True
    fallback_available = True
    user_message = "服务暂时不可用，请稍后重试"


class MediumSeverityException(EnhancedException):
    """中等严重性异常"""
    severity = ErrorSeverity.MEDIUM
    retryable = True
    max_retries = 3
    retry_delay = 1.0
    fallback_available = True
    user_message = "操作失败，请重试"


class LowSeverityException(EnhancedException):
    """低严重性异常"""
    severity = ErrorSeverity.LOW
    retryable = True
    max_retries = 1
    retry_delay = 0.5
    user_message = "请求参数有误，请检查后重试"


# ============================================================================
# 具体业务异常
# ============================================================================

class StorageException(HighSeverityException):
    """存储异常"""

    def __init__(self, message: str = "存储操作失败", operation: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if operation:
            details['operation'] = operation
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            details=details,
            **kwargs
        )


class RedisException(StorageException):
    """Redis 异常"""
    fallback_available = True
    user_message = "缓存服务暂时不可用"

    def __init__(self, message: str = "Redis 操作失败", **kwargs):
        super().__init__(
            message=message,
            operation="redis",
            **kwargs
        )


class AIServiceException(HighSeverityException):
    """AI 服务异常"""
    user_message = "AI 服务暂时不可用，请稍后重试"

    def __init__(self, message: str = "AI 服务调用失败", model: Optional[str] = None, timeout: Optional[float] = None, **kwargs):
        details = kwargs.pop('details', {})
        if model:
            details['model'] = model
        if timeout:
            details['timeout'] = f"{timeout}秒"
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            details=details,
            **kwargs
        )


class AITimeoutException(AIServiceException):
    """AI 服务超时"""
    retryable = True
    max_retries = 2
    user_message = "AI 响应超时，请重试"

    def __init__(self, message: str = "AI 服务响应超时", timeout: Optional[float] = None, **kwargs):
        details = kwargs.pop('details', {})
        if timeout:
            details['timeout'] = f"{timeout}秒"
        super().__init__(
            message=message,
            **kwargs
        )


class ValidationException(LowSeverityException):
    """数据验证异常"""
    severity = ErrorSeverity.LOW
    retryable = False
    user_message = "输入数据格式不正确"

    def __init__(self, message: str = "数据验证失败", field: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            **kwargs
        )


class AuthenticationException(MediumSeverityException):
    """认证异常"""
    severity = ErrorSeverity.HIGH
    retryable = False
    requires_alert = True
    user_message = "认证失败，请重新登录"

    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=401,
            **kwargs
        )


class RateLimitException(MediumSeverityException):
    """限流异常"""
    severity = ErrorSeverity.MEDIUM
    retryable = False
    user_message = "请求过于频繁，请稍后再试"

    def __init__(
        self,
        message: str = "请求过于频繁",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        if limit:
            details['limit'] = limit
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            **kwargs
        )


class ConfigurationException(CriticalException):
    """配置异常"""
    user_message = "系统配置错误，请联系管理员"

    def __init__(self, message: str = "配置错误", config_key: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if config_key:
            details['config_key'] = config_key
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            details=details,
            **kwargs
        )


class CircuitBreakerOpenException(HighSeverityException):
    """断路器开启异常"""
    retryable = False
    requires_alert = True
    user_message = "服务暂时不可用，正在恢复中"

    def __init__(self, service: str, retry_after: int = 60, **kwargs):
        details = kwargs.pop('details', {})
        details.update({
            'service': service,
            'retry_after': retry_after
        })
        super().__init__(
            message=f"断路器已开启: {service}",
            error_code="CIRCUIT_BREAKER_OPEN",
            details=details,
            **kwargs
        )


class RefusalException(EnhancedException):
    """用户拒绝异常（业务正常流程）"""
    severity = ErrorSeverity.LOW
    retryable = False
    requires_alert = False
    user_message = "已了解您的选择"
    status_code = 200

    def __init__(self, message: str = "用户拒绝继续", **kwargs):
        super().__init__(
            message=message,
            error_code="REFUSAL_DETECTED",
            details={},
            **kwargs
        )
