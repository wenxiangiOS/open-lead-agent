"""
连接池管理器 - 统一管理所有连接池

整合了原本分散在各服务中的连接池配置：
- AIService 中的 httpx.Limits
- RedisService 中的 ConnectionPool
"""

import logging
from typing import Optional, Dict, Any

import httpx
from redis.asyncio.connection import ConnectionPool as AsyncConnectionPool
from redis.connection import ConnectionPool as SyncConnectionPool
from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    连接池管理器

    统一管理所有连接池：
    1. HTTP 连接池（用于 AI API）
    2. Redis 异步连接池
    3. Redis 同步连接池
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化连接池管理器

        Args:
            config: 连接池配置（可选，使用默认配置）
        """
        self.config = config or self._get_default_config()

        # 连接池实例
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_async_pool: Optional[AsyncConnectionPool] = None
        self._redis_sync_pool: Optional[SyncConnectionPool] = None
        self._redis_async_client: Optional[AsyncRedis] = None
        self._redis_sync_client: Optional[SyncRedis] = None

        logger.info(
            f"ConnectionPoolManager initialized: "
            f"http_pool={self.config['http_pool_size']}, "
            f"redis_pool={self.config['redis_pool_size']}"
        )

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # HTTP 连接池
            "http_pool_size": settings.http_connections or 50,
            "http_max_keepalive": settings.http_max_keepalive or 10,
            "http_timeout": 60,

            # Redis 连接池
            "redis_pool_size": 50,
            "redis_timeout": 5,
            "redis_host": settings.redis_host or "localhost",
            "redis_port": settings.redis_port or 6379,
            "redis_db": settings.redis_db or 0,
            "redis_password": settings.redis_password,
        }

    async def get_http_client(self) -> httpx.AsyncClient:
        """
        获取 HTTP 客户端（连接池）

        Returns:
            httpx.AsyncClient: HTTP 客户端
        """
        if self._http_client is None:
            limits = httpx.Limits(
                max_connections=self.config["http_pool_size"],
                max_keepalive_connections=self.config["http_max_keepalive"]
            )
            timeout = httpx.Timeout(
                connect=10,
                read=self.config["http_timeout"],
                write=10,
                pool=5
            )

            self._http_client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                verify=True
            )
            logger.info("HTTP client created with connection pool")

        return self._http_client

    async def get_redis_async_pool(self) -> AsyncConnectionPool:
        """
        获取 Redis 异步连接池

        Returns:
            AsyncConnectionPool: Redis 异步连接池
        """
        if self._redis_async_pool is None:
            self._redis_async_pool = AsyncConnectionPool(
                host=self.config["redis_host"],
                port=self.config["redis_port"],
                db=self.config["redis_db"],
                password=self.config["redis_password"],
                decode_responses=True,
                max_connections=self.config["redis_pool_size"],
                socket_keepalive=True,
                socket_connect_timeout=self.config["redis_timeout"],
                socket_timeout=self.config["redis_timeout"],
                retry_on_timeout=True,
                health_check_interval=30,
            )
            logger.info("Redis async pool created")

        return self._redis_async_pool

    async def get_redis_async_client(self) -> AsyncRedis:
        """
        获取 Redis 异步客户端

        Returns:
            AsyncRedis: Redis 异步客户端
        """
        if self._redis_async_client is None:
            pool = await self.get_redis_async_pool()
            self._redis_async_client = AsyncRedis(connection_pool=pool)
            logger.info("Redis async client created")

        return self._redis_async_client

    def get_redis_sync_pool(self) -> SyncConnectionPool:
        """
        获取 Redis 同步连接池

        Returns:
            SyncConnectionPool: Redis 同步连接池
        """
        if self._redis_sync_pool is None:
            self._redis_sync_pool = SyncConnectionPool(
                host=self.config["redis_host"],
                port=self.config["redis_port"],
                db=self.config["redis_db"],
                password=self.config["redis_password"],
                decode_responses=True,
                max_connections=self.config["redis_pool_size"],
                socket_keepalive=True,
                socket_timeout=self.config["redis_timeout"],
                socket_connect_timeout=self.config["redis_timeout"],
                retry_on_timeout=True,
            )
            logger.info("Redis sync pool created")

        return self._redis_sync_pool

    def get_redis_sync_client(self) -> SyncRedis:
        """
        获取 Redis 同步客户端

        Returns:
            SyncRedis: Redis 同步客户端
        """
        if self._redis_sync_client is None:
            pool = self.get_redis_sync_pool()
            self._redis_sync_client = SyncRedis(connection_pool=pool)
            logger.info("Redis sync client created")

        return self._redis_sync_client

    async def health_check(self) -> Dict[str, bool]:
        """
        健康检查

        Returns:
            Dict[str, bool]: 各组件的健康状态
        """
        health_status = {}

        # 检查 HTTP 客户端
        if self._http_client is not None:
            try:
                # 简单的健康检查
                health_status["http_client"] = True
            except Exception as e:
                logger.error(f"HTTP client health check failed: {e}")
                health_status["http_client"] = False
        else:
            health_status["http_client"] = None  # 未初始化

        # 检查 Redis 客户端
        if self._redis_async_client is not None:
            try:
                await self._redis_async_client.ping()
                health_status["redis_async"] = True
            except Exception as e:
                logger.error(f"Redis async health check failed: {e}")
                health_status["redis_async"] = False
        else:
            health_status["redis_async"] = None

        if self._redis_sync_client is not None:
            try:
                self._redis_sync_client.ping()
                health_status["redis_sync"] = True
            except Exception as e:
                logger.error(f"Redis sync health check failed: {e}")
                health_status["redis_sync"] = False
        else:
            health_status["redis_sync"] = None

        return health_status

    async def close(self):
        """关闭所有连接池"""
        # 关闭 HTTP 客户端
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("HTTP client closed")

        # 关闭 Redis 异步客户端
        if self._redis_async_client:
            await self._redis_async_client.close()
            self._redis_async_client = None
            logger.info("Redis async client closed")

        # 关闭 Redis 同步客户端
        if self._redis_sync_client:
            self._redis_sync_client.close()
            self._redis_sync_client = None
            logger.info("Redis sync client closed")

        # 关闭连接池
        if self._redis_async_pool:
            await self._redis_async_pool.disconnect()
            self._redis_async_pool = None
            logger.info("Redis async pool closed")

        if self._redis_sync_pool:
            self._redis_sync_pool.disconnect()
            self._redis_sync_pool = None
            logger.info("Redis sync pool closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 全局连接池管理器实例
_connection_pool_manager: Optional[ConnectionPoolManager] = None


def get_connection_pool_manager() -> ConnectionPoolManager:
    """获取全局连接池管理器实例"""
    global _connection_pool_manager
    if _connection_pool_manager is None:
        _connection_pool_manager = ConnectionPoolManager()
    return _connection_pool_manager
