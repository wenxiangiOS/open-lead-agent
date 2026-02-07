"""
并发管理器 - 统一的并发管理入口

这是并发模块的统一入口，整合了：
- 限流器
- 连接池
- 信号量
- 配置
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from .config import ConcurrencyConfig
from .rate_limiter import UnifiedRateLimiter, RateLimitResult
from .connection_pool import ConnectionPoolManager

logger = logging.getLogger(__name__)


class ConcurrencyManager:
    """
    并发管理器 - 统一的并发管理入口

    这是并发模块的统一入口，提供：
    1. 限流检查
    2. 连接池管理
    3. 并发控制（信号量）
    4. 统一配置
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        """
        初始化并发管理器

        Args:
            config: 并发配置（可选，使用默认配置）
        """
        self.config = config or ConcurrencyConfig()

        # 初始化子模块
        self.rate_limiter = UnifiedRateLimiter(
            default_limit=self.config.user_rate_limit,
            default_window=self.config.user_rate_window
        )
        self.connection_pool = ConnectionPoolManager()

        # 并发信号量
        self._semaphore: Optional[asyncio.Semaphore] = None

        logger.info(
            f"ConcurrencyManager initialized: "
            f"rate_limit={self.config.user_rate_limit}/{self.config.user_rate_window}s, "
            f"max_concurrent={self.config.max_concurrent_requests}"
        )

    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> RateLimitResult:
        """
        检查限流

        Args:
            key: 限流键（用户ID、IP等）
            limit: 限制数量（可选）
            window: 时间窗口（可选）

        Returns:
            RateLimitResult: 限流检查结果
        """
        return await self.rate_limiter.is_allowed(key, limit, window)

    async def check_user_rate_limit(self, user_id: str) -> RateLimitResult:
        """
        检查用户限流（带等级）

        Args:
            user_id: 用户ID

        Returns:
            RateLimitResult: 限流检查结果
        """
        return await self.rate_limiter.check_tiered_limit(user_id)

    def set_user_tier(self, user_id: str, tier: str) -> None:
        """
        设置用户等级

        Args:
            user_id: 用户ID
            tier: 用户等级
        """
        self.rate_limiter.set_user_tier(user_id, tier)

    def get_user_tier(self, user_id: str) -> str:
        """
        获取用户等级

        Args:
            user_id: 用户ID

        Returns:
            str: 用户等级
        """
        return self.rate_limiter.get_user_tier(user_id)

    async def get_http_client(self):
        """获取 HTTP 客户端"""
        return await self.connection_pool.get_http_client()

    async def get_redis_async_client(self):
        """获取 Redis 异步客户端"""
        return await self.connection_pool.get_redis_async_client()

    def get_redis_sync_client(self):
        """获取 Redis 同步客户端"""
        return self.connection_pool.get_redis_sync_client()

    async def acquire_semaphore(self):
        """
        获取并发信号量

        用于限制最大并发请求数
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

        await self._semaphore.acquire()
        return self._semaphore

    def release_semaphore(self, semaphore: asyncio.Semaphore):
        """
        释放并发信号量

        Args:
            semaphore: 信号量实例
        """
        semaphore.release()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def close(self):
        """关闭所有资源"""
        await self.connection_pool.close()
        logger.info("ConcurrencyManager closed")

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态
        """
        health_status = {
            "config": {
                "rate_limit_enabled": self.config.rate_limit_enabled,
                "user_rate_limit": self.config.user_rate_limit,
                "max_concurrent_requests": self.config.max_concurrent_requests,
            },
            "components": await self.connection_pool.health_check()
        }

        return health_status


# 全局并发管理器实例
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """获取全局并发管理器实例"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager
