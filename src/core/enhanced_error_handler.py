"""
增强的错误处理器

提供错误分类、自动恢复、告警、降级等完整功能
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, Any, Optional, Callable, Type
from functools import wraps

from .error_severity import ErrorSeverity
from .enhanced_exceptions import EnhancedException
from .logging import StructuredLogger

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    增强的错误处理器

    功能：
    1. 错误分类和分级
    2. 结构化日志记录
    3. 自动恢复策略
    4. 生产环境告警
    5. 用户友好的错误响应
    """

    # 敏感信息关键词（需要脱敏）
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'pwd',
        'token', 'api_key', 'apikey', 'api-key',
        'secret', 'access_key', 'secret_key',
        'phone', 'mobile', 'telephone',
        'id_card', 'idcard', 'ssn'
    ]

    # 错误分类映射
    ERROR_CLASSIFICATION: Dict[Type[Exception], ErrorSeverity] = {
        # 连接相关
        ConnectionError: ErrorSeverity.HIGH,
        TimeoutError: ErrorSeverity.MEDIUM,

        # 数据相关
        ValueError: ErrorSeverity.LOW,
        TypeError: ErrorSeverity.LOW,
        KeyError: ErrorSeverity.MEDIUM,
    }

    # 恢复策略
    RECOVERY_STRATEGIES = {
        ErrorSeverity.CRITICAL: ["alert", "shutdown"],
        ErrorSeverity.HIGH: ["alert", "circuit_breaker", "fallback"],
        ErrorSeverity.MEDIUM: ["retry", "fallback", "log"],
        ErrorSeverity.LOW: ["log", "continue"],
    }

    def __init__(self):
        """初始化错误处理器"""
        self._alert_callbacks: list[Callable] = []
        self._error_counts: Dict[str, int] = {}
        self._last_alert_time: Dict[str, float] = {}

    def register_alert_callback(self, callback: Callable):
        """
        注册告警回调函数

        Args:
            callback: 告警回调，签名: callback(error, severity, context)
        """
        self._alert_callbacks.append(callback)

    def handle(
        self,
        error: Exception,
        context: str = "",
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        统一处理错误

        Args:
            error: 异常对象
            context: 错误上下文
            user_id: 用户ID
            request_id: 请求ID

        Returns:
            错误响应字典
        """
        # 1. 确保是增强异常
        enhanced_error = self._ensure_enhanced_exception(error, context)

        # 2. 记录错误统计
        self._record_error(enhanced_error)

        # 3. 记录结构化日志
        self._log_error(enhanced_error, context, user_id, request_id)

        # 4. 尝试恢复
        recovery_result = self._attempt_recovery(enhanced_error)
        if recovery_result is not None:
            return recovery_result

        # 5. 发送告警（如果需要）
        if enhanced_error.should_alert_team:
            self._send_alert(enhanced_error, context, user_id)

        # 6. 构建响应
        return self._build_response(enhanced_error)

    def _ensure_enhanced_exception(
        self,
        error: Exception,
        context: str
    ) -> EnhancedException:
        """确保返回增强异常"""
        if isinstance(error, EnhancedException):
            return error

        # 普通异常转换为增强异常
        from .enhanced_exceptions import MediumSeverityException

        # 根据异常类型确定严重性
        severity = self._classify_error(error)

        # 创建对应的增强异常
        if severity == ErrorSeverity.CRITICAL:
            from .enhanced_exceptions import CriticalException
            return CriticalException.from_exception(error)
        elif severity == ErrorSeverity.HIGH:
            from .enhanced_exceptions import HighSeverityException
            return HighSeverityException.from_exception(error)
        else:
            return MediumSeverityException.from_exception(error)

    def _classify_error(self, error: Exception) -> ErrorSeverity:
        """
        分类错误严重性

        Args:
            error: 异常对象

        Returns:
            错误严重性等级
        """
        # 检查是否是已知异常类型
        for error_type, severity in self.ERROR_CLASSIFICATION.items():
            if isinstance(error, error_type):
                return severity

        # 根据异常名称判断
        error_name = type(error).__name__
        if 'timeout' in error_name.lower():
            return ErrorSeverity.MEDIUM
        if 'connection' in error_name.lower():
            return ErrorSeverity.HIGH
        if 'critical' in error_name.lower():
            return ErrorSeverity.CRITICAL

        # 默认中等严重性
        return ErrorSeverity.MEDIUM

    def _record_error(self, error: EnhancedException):
        """
        记录错误统计

        Args:
            error: 增强异常
        """
        error_key = f"{error.error_code}:{error.message}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

    def _log_error(
        self,
        error: EnhancedException,
        context: str,
        user_id: Optional[str],
        request_id: Optional[str]
    ):
        """
        记录结构化错误日志

        Args:
            error: 增强异常
            context: 错误上下文
            user_id: 用户ID
            request_id: 请求ID
        """
        # 构建日志数据
        log_data = {
            "error_code": error.error_code,
            "severity": error.severity.name,
            "sanitized_message": self._sanitize_message(error.message),
            "context": context,
            "retryable": error.is_retryable,
            "has_fallback": error.has_fallback,
        }

        if user_id:
            log_data["user_id"] = self._sanitize_value(user_id)

        if request_id:
            log_data["request_id"] = request_id

        if error.context:
            log_data["error_context"] = error.context

        # 根据严重性选择日志级别
        if error.severity <= ErrorSeverity.HIGH:
            logger.error(
                f"[{error.severity.name}] {error.error_code}: {error.message}",
                extra=log_data,
                exc_info=True
            )
        else:
            logger.warning(
                f"[{error.severity.name}] {error.error_code}: {error.message}",
                extra=log_data
            )

    def _sanitize_message(self, message: str) -> str:
        """
        脱敏处理错误消息

        Args:
            message: 原始消息

        Returns:
            脱敏后的消息
        """
        import re

        safe_message = message
        for keyword in self.SENSITIVE_KEYWORDS:
            pattern = rf'({keyword}["\']?\s*[:=]\s*["\']?)[^"\']+(["\']?)'
            safe_message = re.sub(
                pattern,
                rf'\1****\2',
                safe_message,
                flags=re.IGNORECASE
            )
        return safe_message

    def _sanitize_value(self, value: str) -> str:
        """脱敏单个值"""
        if len(value) <= 4:
            return "****"
        return value[:2] + "****" + value[-2:]

    def _attempt_recovery(self, error: EnhancedException) -> Optional[Dict[str, Any]]:
        """
        尝试从错误中恢复

        Args:
            error: 增强异常

        Returns:
            恢复成功时的响应，None 表示无法恢复
        """
        # Redis/存储错误：自动降级到内存存储
        # 检查是否是 RedisException 或由连接/超时错误引起
        from .enhanced_exceptions import RedisException

        is_redis_error = (
            isinstance(error, RedisException) or
            (error.cause and isinstance(error.cause, (ConnectionError, TimeoutError)))
        )

        if is_redis_error:
            try:
                from src.repositories import get_storage_factory
                factory = get_storage_factory()
                factory.switch_to_memory_only()
                logger.info("✅ 已自动切换到内存存储模式")

                return {
                    "success": True,
                    "warning": "缓存服务暂时不可用，已切换到备用存储",
                    "severity": error.severity.name
                }
            except Exception as e:
                logger.error(f"❌ 降级失败: {e}")

        # 其他错误不尝试恢复
        return None

    def _send_alert(
        self,
        error: EnhancedException,
        context: str,
        user_id: Optional[str]
    ):
        """
        发送告警

        Args:
            error: 增强异常
            context: 错误上下文
            user_id: 用户ID
        """
        error_key = f"{error.error_code}:{error.message}"

        # 避免频繁告警（1小时内相同错误只告警一次）
        current_time = time.time()
        last_alert = self._last_alert_time.get(error_key, 0)

        if current_time - last_alert < 3600:  # 1小时
            return

        # 记录告警时间
        self._last_alert_time[error_key] = current_time

        # 调用所有告警回调
        for callback in self._alert_callbacks:
            try:
                callback(error, context, user_id)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")

    def _build_response(self, error: EnhancedException) -> Dict[str, Any]:
        """
        构建错误响应

        Args:
            error: 增强异常

        Returns:
            错误响应字典
        """
        # 开发环境包含调试信息
        from src.config import settings
        include_debug = settings.app.is_development

        return error.to_dict(include_debug=include_debug)

    def get_error_stats(self) -> Dict[str, int]:
        """
        获取错误统计

        Returns:
            错误计数字典
        """
        return self._error_counts.copy()


# ============================================================================
# 装饰器
# ============================================================================

def handle_errors(
    context: str = "",
    fallback_result: Any = None,
    reraise: bool = False
):
    """
    错误处理装饰器

    Args:
        context: 错误上下文描述
        fallback_result: 发生错误时的默认返回值
        reraise: 是否重新抛出异常

    Usage:
        @handle_errors(context="用户登录", fallback_result={"success": False})
        async def login(username, password):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handler = error_handler
                result = handler.handle(e, context)

                if reraise:
                    raise

                if fallback_result is not None:
                    return fallback_result

                return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = error_handler
                result = handler.handle(e, context)

                if reraise:
                    raise

                if fallback_result is not None:
                    return fallback_result

                return result

        # 检测函数是否是协程函数
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    错误重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟
        backoff: 退避倍数
        exceptions: 需要重试的异常类型

    Usage:
        @retry_on_error(max_retries=3, exceptions=(ConnectionError,))
        async def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"重试 {attempt + 1}/{max_retries}: {func.__name__} - {str(e)}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"重试失败 {max_retries} 次: {func.__name__}"
                        )

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"重试 {attempt + 1}/{max_retries}: {func.__name__} - {str(e)}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"重试失败 {max_retries} 次: {func.__name__}"
                        )

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 全局实例
# ============================================================================

error_handler = ErrorHandler()


# ============================================================================
# 便捷函数
# ============================================================================

def handle_error(
    error: Exception,
    context: str = "",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    便捷的错误处理函数

    Args:
        error: 异常对象
        context: 错误上下文
        user_id: 用户ID

    Returns:
        错误响应字典
    """
    return error_handler.handle(error, context, user_id)
