"""
错误处理工具

统一的错误处理模式，消除重复的 try-except 代码
"""

import asyncio
import logging
from functools import wraps
from typing import Optional, Any, Callable, Type, Tuple

from src.core import error_handler, ErrorSeverity

logger = logging.getLogger(__name__)


# ============================================================================
# 错误处理装饰器
# ============================================================================

def safe_execute(
    default_return: Any = None,
    fallback_value: Any = None,
    log_errors: bool = True,
    context: str = ""
):
    """
    安全执行装饰器

    自动捕获异常并记录日志

    Args:
        default_return: 发生异常时的返回值
        fallback_value: 降级使用的值
        log_errors: 是否记录错误日志
        context: 错误上下文描述

    Usage:
        @safe_execute(default_return={}, context="用户登录")
        async def login(username, password):
            return await authenticate_user(username, password)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"[{context}] 函数 {func.__name__} 执行失败: {e}")

                # 使用错误处理器
                error_handler.handle(e, context)
                return fallback_value if fallback_value is not None else default_return
            except:
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"[{context}] 函数 {func.__name__} 执行失败: {e}")

                error_handler.handle(e, context)
                return fallback_value if fallback_value is not None else default_return

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    失败重试装饰器

    自动重试失败的操作

    Args:
        max_attempts: 最大尝试次数
        delay: 初始重试延迟
        backoff: 退避倍数
        exceptions: 需要重试的异常类型

    Usage:
        @retry_on_failure(max_attempts=3, exceptions=(ConnectionError,))
        async def fetch_data():
            return await database.query()
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt}/{max_attempts} 次尝试失败: {e}，"
                            f"{current_delay}秒后重试..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败"
                        )
                        raise

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt}/{max_attempts} 次尝试失败: {e}，"
                            f"{current_delay}秒后重试..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败"
                        )
                        raise

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def ignore_errors(
    default_return: Any = None,
    log_level: str = "warning"
):
    """
    忽略错误装饰器

    静默处理异常，适用于非关键操作

    Args:
        default_return: 发生异常时的返回值
        log_level: 日志级别

    Usage:
        @ignore_errors(default_return=False)
        async def log_analytics(event):
            # 记录分析事件，失败不影响主流程
            await analytics.track(event)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level)
                log_func(f"忽略错误 [{func.__name__}]: {e}")
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level)
                log_func(f"忽略错误 [{func.__name__}]: {e}")
                return default_return

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_error_handling(
    error_types: Tuple[Type[Exception], ...] = (Exception,),
    fallback: Optional[Callable] = None,
    raise_on_error: bool = False
):
    """
    通用错误处理装饰器

    Args:
        error_types: 要捕获的异常类型
        fallback: 降级函数
        raise_on_error: 是否重新抛出异常

    Usage:
        def fallback_error(error):
            return {"error": str(error)}

        @with_error_handling((ValueError, TypeError), fallback=fallback_error)
        def process_data(data):
            return int(data)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except error_types as e:
                logger.warning(f"函数 {func.__name__} 出错: {e}")

                if fallback:
                    return fallback(e)

                if raise_on_error:
                    raise

                # 返回 None 或默认值
                return None

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                logger.warning(f"函数 {func.__name__} 出错: {e}")

                if fallback:
                    return fallback(e)

                if raise_on_error:
                    raise

                return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 上下文管理器
# ============================================================================

class ErrorContext:
    """
    错误上下文管理器

    自动记录执行时间、错误等信息
    """

    def __init__(self, operation_name: str, user_id: Optional[str] = None):
        """
        初始化错误上下文

        Args:
            operation_name: 操作名称
            user_id: 用户ID
        """
        self.operation_name = operation_name
        self.user_id = user_id
        self.start_time = None
        self.end_time = None
        self.error = None
        self.success = False

    def __enter__(self):
        """进入上下文"""
        import time
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        import time
        self.end_time = time.time()

        if exc_type is not None:
            self.error = exc_val
            self.success = False
            logger.error(
                f"[{self.operation_name}] 执行失败 "
                f"耗时: {self._get_duration():.2f}ms, 错误: {exc_val}"
            )
        else:
            self.success = True
            logger.debug(
                f"[{self.operation_name}] 执行成功 "
                f"耗时: {self._get_duration():.2f}ms"
            )

        return False  # 不抑制异常

    def _get_duration(self) -> float:
        """获取执行耗时（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


# ============================================================================
# 便捷函数
# ============================================================================

def execute_safely(
    func: Callable,
    *args,
    context: str = "",
    default_value: Any = None,
    **kwargs
) -> Any:
    """
    安全执行函数

    Args:
        func: 要执行的函数
        *args: 位置参数
        context: 错误上下文
        default_value: 默认返回值
        **kwargs: 关键字参数

    Returns:
        函数执行结果或默认值
    """
    try:
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"[{context}] 函数 {func.__name__} 执行失败: {e}")
        error_handler.handle(e, context)
        return default_value


async def execute_safely_async(
    func: Callable,
    *args,
    context: str = "",
    default_value: Any = None,
    **kwargs
) -> Any:
    """
    异步安全执行函数

    Args:
        func: 要执行的异步函数
        *args: 位置参数
        context: 错误上下文
        default_value: 默认返回值
        **kwargs: 关键字参数

    Returns:
        函数执行结果或默认值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"[{context}] 异步函数 {func.__name__} 执行失败: {e}")
        error_handler.handle(e, context)
        return default_value
