"""
断路器模式实现

防止级联故障，提高系统健壮性
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Any, Dict
from enum import Enum, auto

from .enhanced_exceptions import CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = auto()      # 关闭：正常工作
    OPEN = auto()        # 开启：故障状态，拒绝请求
    HALF_OPEN = auto()   # 半开：尝试恢复


class CircuitBreaker:
    """
    断路器实现

    防止故障服务被持续调用，导致级联故障
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        half_open_max_calls: int = 3
    ):
        """
        初始化断路器

        Args:
            name: 断路器名称（标识服务）
            failure_threshold: 失败阈值（连续失败多少次后开启断路器）
            recovery_timeout: 恢复超时（断路器开启后多久尝试恢复）
            expected_exception: 预期的异常类型
            half_open_max_calls: 半开状态最大允许调用数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        # 状态
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0
        self._half_open_calls = 0

        # 统计
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0

        # 锁（用于并发控制）
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    @property
    def is_open(self) -> bool:
        """断路器是否开启"""
        # 如果是开启状态，检查是否可以恢复
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and time.time() - self._last_failure_time >= self.recovery_timeout:
                logger.info(f"断路器 [{self.name}] 尝试恢复: 切换到半开状态")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                return False
            return True
        return False

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过断路器调用函数

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpenException: 断路器开启时
            Exception: 函数执行异常
        """
        async with self._lock:
            self._total_calls += 1

            # 检查断路器状态
            if self.is_open:
                logger.warning(f"断路器 [{self.name}] 已开启，拒绝调用")
                raise CircuitBreakerOpenException(
                    service=self.name,
                    retry_after=self.recovery_timeout
                )

            # 半开状态限制调用次数
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls > self.half_open_max_calls:
                    logger.warning(f"断路器 [{self.name}] 半开状态调用次数超限，重新开启")
                    self._state = CircuitState.OPEN
                    self._last_failure_time = time.time()
                    raise CircuitBreakerOpenException(
                        service=self.name,
                        retry_after=self.recovery_timeout
                    )

        try:
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 成功：更新状态
            async with self._lock:
                self._on_success()

            return result

        except self.expected_exception as e:
            # 失败：更新状态
            async with self._lock:
                self._on_failure()
            raise

        except Exception as e:
            # 未预期的异常：也记录为失败
            async with self._lock:
                self._on_failure()
            raise

    def _on_success(self):
        """处理成功调用"""
        self._success_count = 0
        self._total_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"断路器 [{self.name}] 半开状态调用成功，切换到关闭状态")
            self._state = CircuitState.CLOSED
            self._half_open_calls = 0

    def _on_failure(self):
        """处理失败调用"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._total_failures += 1

        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.warning(
                    f"断路器 [{self.name}] 失败次数达到阈值 "
                    f"({self.failure_count}/{self.failure_threshold})，开启断路器"
                )
                self._state = CircuitState.OPEN

    def get_stats(self) -> Dict[str, Any]:
        """
        获取断路器统计信息

        Returns:
            统计信息字典
        """
        success_rate = 0
        if self._total_calls > 0:
            success_rate = self._total_successes / self._total_calls

        return {
            "name": self.name,
            "state": self._state.name,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "success_rate": f"{success_rate:.2%}",
            "last_failure_time": self._last_failure_time
        }

    def reset(self):
        """重置断路器"""
        logger.info(f"断路器 [{self.name}] 已重置")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        self._half_open_calls = 0


class CircuitBreakerManager:
    """断路器管理器"""

    def __init__(self):
        """初始化断路器管理器"""
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """
        获取或创建断路器

        Args:
            name: 断路器名称
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时
            expected_exception: 预期的异常类型

        Returns:
            断路器实例
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
        return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有断路器的统计信息

        Returns:
            统计信息字典
        """
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self):
        """重置所有断路器"""
        for breaker in self._breakers.values():
            breaker.reset()

    def reset_breaker(self, name: str):
        """
        重置指定断路器

        Args:
            name: 断路器名称
        """
        if name in self._breakers:
            self._breakers[name].reset()


# ============================================================================
# 全局实例
# ============================================================================

circuit_breaker_manager = CircuitBreakerManager()


# ============================================================================
# 装饰器
# ============================================================================

def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    exceptions: tuple = (Exception,)
):
    """
    断路器装饰器

    Args:
        name: 断路器名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时
        exceptions: 需要断路的异常类型

    Usage:
        @with_circuit_breaker("ai_service", failure_threshold=3)
        async def call_ai():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = circuit_breaker_manager.get_breaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=exceptions[0]
            )
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = circuit_breaker_manager.get_breaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=exceptions[0]
            )
            return asyncio.run(breaker.call(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 导入 wraps
from functools import wraps
