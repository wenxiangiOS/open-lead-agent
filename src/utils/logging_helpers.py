"""
日志工具

统一的日志记录模式，消除重复的日志代码
"""

import logging
import time
import json
from typing import Any, Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from datetime import datetime

from src.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# 结构化日志
# ============================================================================

class StructuredLogger:
    """
    结构化日志记录器

    提供统一的日志格式，支持 JSON 输出
    """

    def __init__(self, name: str):
        """
        初始化结构化日志记录器

        Args:
            name: 日志记录器名称
        """
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}

    def with_context(self, **kwargs) -> 'StructuredLogger':
        """
        添加上下文

        Args:
            **kwargs: 上下文键值对

        Returns:
            自身，支持链式调用
        """
        self._context.update(kwargs)
        return self

    def clear_context(self) -> 'StructuredLogger':
        """清空上下文"""
        self._context.clear()
        return self

    def _log(
        self,
        level: int,
        message: str,
        **kwargs
    ):
        """
        记录日志

        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 额外的日志字段
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            **self._context,
            **kwargs
        }

        # 根据配置决定输出格式
        if settings.logging.json_enabled:
            log_message = json.dumps(log_data, ensure_ascii=False)
        else:
            # 平面格式
            parts = [f"{k}={v}" for k, v in log_data.items()]
            log_message = " | ".join(parts)

        self.logger.log(level, log_message)

    def debug(self, message: str, **kwargs):
        """调试级别日志"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """信息级别日志"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """警告级别日志"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """错误级别日志"""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """严重错误级别日志"""
        self._log(logging.CRITICAL, message, **kwargs)


# ============================================================================
# 性能日志装饰器
# ============================================================================

def log_execution_time(
    threshold_ms: Optional[float] = None,
    log_args: bool = False,
    log_result: bool = False
):
    """
    记录函数执行时间的装饰器

    Args:
        threshold_ms: 仅当执行时间超过此阈值时记录（毫秒）
        log_args: 是否记录参数
        log_result: 是否记录返回值

    Usage:
        @log_execution_time(threshold_ms=100)
        async def process_data(data):
            return await api.call(data)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                if threshold_ms is None or elapsed_ms > threshold_ms:
                    log_data = {
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "success"
                    }

                    if log_args:
                        log_data["args"] = str(args)[:200]
                        log_data["kwargs"] = str(kwargs)[:200]

                    if log_result:
                        log_data["result"] = str(result)[:200]

                    logger.info(
                        f"[{func_name}] 执行完成",
                        extra=log_data
                    )

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"[{func_name}] 执行失败: {e}",
                    extra={
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                if threshold_ms is None or elapsed_ms > threshold_ms:
                    log_data = {
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "success"
                    }

                    if log_args:
                        log_data["args"] = str(args)[:200]
                        log_data["kwargs"] = str(kwargs)[:200]

                    if log_result:
                        log_data["result"] = str(result)[:200]

                    logger.info(
                        f"[{func_name}] 执行完成",
                        extra=log_data
                    )

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"[{func_name}] 执行失败: {e}",
                    extra={
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 请求日志装饰器
# ============================================================================

def log_api_call(
    log_request_body: bool = False,
    log_response_body: bool = False,
    sanitize_fields: list = None
):
    """
    API 调用日志装饰器

    Args:
        log_request_body: 是否记录请求体
        log_response_body: 是否记录响应体
        sanitize_fields: 需要脱敏的字段列表

    Usage:
        @log_api_call(sanitize_fields=["password", "token"])
        async def login(username, password):
            return await auth_service.login(username, password)
    """
    sanitize_fields = sanitize_fields or ["password", "token", "secret", "key"]

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.time()

            # 记录请求
            request_log = {"function": func_name}

            if log_request_body and kwargs:
                sanitized = _sanitize_dict(kwargs, sanitize_fields)
                request_log["request"] = str(sanitized)[:500]

            logger.info(f"[{func_name}] API 调用开始", extra=request_log)

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                # 记录响应
                response_log = {
                    "function": func_name,
                    "duration_ms": round(elapsed_ms, 2),
                    "status": "success"
                }

                if log_response_body:
                    sanitized = _sanitize_dict(result, sanitize_fields)
                    response_log["response"] = str(sanitized)[:500]

                logger.info(f"[{func_name}] API 调用成功", extra=response_log)

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"[{func_name}] API 调用失败: {e}",
                    extra={
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.time()

            request_log = {"function": func_name}

            if log_request_body and kwargs:
                sanitized = _sanitize_dict(kwargs, sanitize_fields)
                request_log["request"] = str(sanitized)[:500]

            logger.info(f"[{func_name}] API 调用开始", extra=request_log)

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                response_log = {
                    "function": func_name,
                    "duration_ms": round(elapsed_ms, 2),
                    "status": "success"
                }

                if log_response_body:
                    sanitized = _sanitize_dict(result, sanitize_fields)
                    response_log["response"] = str(sanitized)[:500]

                logger.info(f"[{func_name}] API 调用成功", extra=response_log)

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"[{func_name}] API 调用失败: {e}",
                    extra={
                        "function": func_name,
                        "duration_ms": round(elapsed_ms, 2),
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 性能追踪上下文管理器
# ============================================================================

@contextmanager
def log_performance(operation_name: str, threshold_ms: Optional[float] = None):
    """
    性能追踪上下文管理器

    Args:
        operation_name: 操作名称
        threshold_ms: 仅当执行时间超过此阈值时记录

    Usage:
        with log_performance("数据库查询", threshold_ms=100):
            result = database.query(...)
    """
    start_time = time.time()

    try:
        yield
    finally:
        elapsed_ms = (time.time() - start_time) * 1000

        if threshold_ms is None or elapsed_ms > threshold_ms:
            logger.info(
                f"[{operation_name}] 执行完成",
                extra={
                    "operation": operation_name,
                    "duration_ms": round(elapsed_ms, 2)
                }
            )


# ============================================================================
# 辅助函数
# ============================================================================

def _sanitize_dict(data: Any, sensitive_fields: list) -> Any:
    """
    脱敏字典中的敏感字段

    Args:
        data: 要脱敏的数据
        sensitive_fields: 敏感字段列表

    Returns:
        脱敏后的数据
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in [f.lower() for f in sensitive_fields]:
                sanitized[key] = "***"
            elif isinstance(value, (dict, list)):
                sanitized[key] = _sanitize_dict(value, sensitive_fields)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_dict(item, sensitive_fields) for item in data]
    else:
        return data


def get_logger(name: str) -> StructuredLogger:
    """
    获取结构化日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        结构化日志记录器实例
    """
    return StructuredLogger(name)


# ============================================================================
# 预配置的日志记录器
# ============================================================================

# API 日志记录器
api_logger = StructuredLogger("src.api")

# 服务日志记录器
service_logger = StructuredLogger("src.services")

# 数据库日志记录器
db_logger = StructuredLogger("src.database")

# 缓存日志记录器
cache_logger = StructuredLogger("src.cache")
