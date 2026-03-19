"""
健康检查系统

提供系统、服务和依赖的健康状态检查
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 健康状态
# ============================================================================

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级（部分功能不可用）
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"       # 未知


# ============================================================================
# 健康检查结果
# ============================================================================

@dataclass
class HealthCheckResult:
    """
    健康检查结果

    Attributes:
        name: 检查项名称
        status: 健康状态
        message: 状态消息
        details: 详细信息
        duration_ms: 检查耗时（毫秒）
        timestamp: 检查时间戳
    """
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """是否降级"""
        return self.status == HealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        """是否不健康"""
        return self.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp
        }


# ============================================================================
# 健康检查器
# ============================================================================

class HealthChecker:
    """
    健康检查器

    负责执行单个健康检查
    """

    def __init__(
        self,
        name: str,
        check_func: Callable,
        timeout: float = 5.0,
        critical: bool = True
    ):
        """
        初始化健康检查器

        Args:
            name: 检查项名称
            check_func: 检查函数（同步或异步）
            timeout: 超时时间（秒）
            critical: 是否为关键检查（关键检查失败会导致整体不健康）
        """
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical

    async def check(self) -> HealthCheckResult:
        """
        执行健康检查

        Returns:
            健康检查结果
        """
        start_time = time.time()

        try:
            # 执行检查函数
            if asyncio.iscoroutinefunction(self.check_func):
                result = await asyncio.wait_for(
                    self.check_func(),
                    timeout=self.timeout
                )
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.check_func),
                    timeout=self.timeout
                )

            # 处理返回结果
            if isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "检查通过" if result else "检查失败"
            elif isinstance(result, HealthCheckResult):
                status = result.status
                message = result.message
            elif isinstance(result, dict):
                status = HealthStatus(result.get("status", HealthStatus.UNKNOWN.value))
                message = result.get("message", "")
            elif isinstance(result, tuple):
                status, message = result[0], result[1] if len(result) > 1 else ""
            else:
                status = HealthStatus.HEALTHY
                message = str(result)

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration_ms
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查超时（{self.timeout}秒）",
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查异常: {str(e)}",
                duration_ms=duration_ms
            )


# ============================================================================
# 健康检查管理器
# ============================================================================

class HealthCheckManager:
    """
    健康检查管理器

    管理所有健康检查器，提供整体健康状态
    """

    def __init__(self):
        """初始化健康检查管理器"""
        self._checkers: Dict[str, HealthChecker] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}

    def register(
        self,
        name: str,
        check_func: Callable,
        timeout: float = 5.0,
        critical: bool = True
    ) -> HealthChecker:
        """
        注册健康检查

        Args:
            name: 检查项名称
            check_func: 检查函数
            timeout: 超时时间
            critical: 是否关键检查

        Returns:
            健康检查器实例

        Usage:
            def check_database():
                return database.is_connected()

            health_manager.register("database", check_database)
        """
        checker = HealthChecker(name, check_func, timeout, critical)
        self._checkers[name] = checker
        logger.info(f"注册健康检查: {name}")
        return checker

    def unregister(self, name: str) -> bool:
        """
        取消注册健康检查

        Args:
            name: 检查项名称

        Returns:
            是否取消成功
        """
        if name in self._checkers:
            del self._checkers[name]
            if name in self._last_results:
                del self._last_results[name]
            logger.info(f"取消注册健康检查: {name}")
            return True
        return False

    async def check(self, name: str) -> HealthCheckResult:
        """
        执行单个健康检查

        Args:
            name: 检查项名称

        Returns:
            健康检查结果
        """
        checker = self._checkers.get(name)
        if not checker:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="检查项不存在"
            )

        result = await checker.check()
        self._last_results[name] = result
        return result

    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        执行所有健康检查

        Returns:
            所有检查结果的字典
        """
        results = {}

        for name in self._checkers.keys():
            results[name] = await self.check(name)

        return results

    async def get_health_status(self) -> Dict[str, Any]:
        """
        获取整体健康状态

        Returns:
            包含整体状态和所有检查结果的字典
        """
        results = await self.check_all()

        # 计算整体状态
        overall_status = HealthStatus.HEALTHY
        unhealthy_count = 0
        degraded_count = 0
        critical_unhealthy = False

        for result in results.values():
            if result.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
                checker = self._checkers.get(result.name)
                if checker and checker.critical:
                    critical_unhealthy = True

            elif result.status == HealthStatus.DEGRADED:
                degraded_count += 1

        # 确定整体状态
        if critical_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        elif unhealthy_count > 0:
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "unhealthy_count": unhealthy_count,
            "degraded_count": degraded_count,
            "total_checks": len(results),
            "checks": {k: v.to_dict() for k, v in results.items()}
        }

    def get_last_result(self, name: str) -> Optional[HealthCheckResult]:
        """获取上次检查结果"""
        return self._last_results.get(name)

    def get_all_last_results(self) -> Dict[str, HealthCheckResult]:
        """获取所有上次检查结果"""
        return dict(self._last_results)


# ============================================================================
# 预定义的健康检查器
# ============================================================================

def create_database_check(connection_func: Callable) -> Callable:
    """
    创建数据库健康检查函数

    Args:
        connection_func: 返回数据库连接的函数

    Returns:
        健康检查函数
    """
    async def check() -> bool:
        try:
            conn = connection_func()
            if asyncio.iscoroutinefunction(connection_func):
                conn = await connection_func()

            # 简单的连接测试
            return conn is not None

        except Exception:
            return False

    return check


def create_redis_check(redis_client) -> Callable:
    """
    创建 Redis 健康检查函数

    Args:
        redis_client: Redis 客户端

    Returns:
        健康检查函数
    """
    async def check() -> bool:
        try:
            # 尝试 PING
            if asyncio.iscoroutinefunction(redis_client.ping):
                return await redis_client.ping()
            else:
                return redis_client.ping()

        except Exception:
            return False

    return check


def create_http_check(url: str, timeout: float = 5.0) -> Callable:
    """
    创建 HTTP 健康检查函数

    Args:
        url: 要检查的 URL
        timeout: 超时时间

    Returns:
        健康检查函数
    """
    async def check() -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                return 200 <= response.status_code < 300

        except Exception:
            return False

    return check


def create_disk_space_check(
    path: str,
    threshold_mb: int = 100
) -> Callable:
    """
    创建磁盘空间检查函数

    Args:
        path: 要检查的路径
        threshold_mb: 最小可用空间（MB）

    Returns:
        健康检查函数
    """
    def check() -> tuple:
        try:
            import shutil
            usage = shutil.disk_usage(path)

            free_mb = usage.free / (1024 * 1024)
            is_healthy = free_mb >= threshold_mb

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            message = f"可用空间: {free_mb:.0f} MB"

            return (status, message)

        except Exception as e:
            return (HealthStatus.UNKNOWN, f"检查失败: {e}")

    return check


def create_memory_check(threshold_percent: float = 90.0) -> Callable:
    """
    创建内存使用检查函数

    Args:
        threshold_percent: 最大使用百分比

    Returns:
        健康检查函数
    """
    def check() -> tuple:
        try:
            import psutil
            memory = psutil.virtual_memory()

            is_healthy = memory.percent < threshold_percent

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            message = f"内存使用: {memory.percent:.1f}%"

            return (status, message)

        except Exception as e:
            return (HealthStatus.UNKNOWN, f"检查失败: {e}")

    return check


# ============================================================================
# 全局健康检查管理器
# ============================================================================

# 默认健康检查管理器
default_health_manager = HealthCheckManager()
