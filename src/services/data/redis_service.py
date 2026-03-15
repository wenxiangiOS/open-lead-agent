"""Redis storage service for high concurrency support

支持：
- 健康检查与自动重连
- 操作超时控制
- 连接池管理
- 同步/异步双模式
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import redis
    from redis.asyncio import Redis as AsyncRedis
    from redis.asyncio.connection import ConnectionPool
    from redis import Redis as SyncRedis
    from redis.connection import ConnectionPool as SyncConnectionPool
    from redis.exceptions import ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis 服务 - 支持高并发、健康检查、自动重连

    特性：
    1. 健康检查 - 定期检查连接状态
    2. 自动重连 - 连接断开时自动恢复
    3. 超时控制 - 所有操作都有超时保护
    4. 连接池管理 - 高效复用连接
    """

    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 5
    HEALTH_CHECK_INTERVAL = 30  # 健康检查间隔（秒）
    MAX_RECONNECT_ATTEMPTS = 3  # 最大重连尝试次数

    def __init__(self):
        """Initialize Redis service"""
        self.enabled = settings.redis_enabled and REDIS_AVAILABLE
        self.client: Optional[AsyncRedis] = None
        self.sync_client: Optional[SyncRedis] = None
        self.pool: Optional[ConnectionPool] = None
        self.sync_pool: Optional[SyncConnectionPool] = None
        self.prefix = settings.redis_prefix

        # 健康状态追踪
        self._is_healthy = True
        self._last_health_check = None
        self._failed_attempts = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = False

        if not REDIS_AVAILABLE:
            logger.warning("Redis not installed. Install with: pip install redis hiredis")
            self.enabled = False
            return

        if not self.enabled:
            logger.info("Redis disabled. Using in-memory storage.")
            return

        # 注意：不在 __init__ 中创建连接，延迟到首次使用时

    async def _ensure_initialized(self):
        """确保已初始化（延迟初始化）"""
        if self._initialized:
            return

        await self._initialize_with_retry()
        self._initialized = True

    async def _initialize_with_retry(self):
        """带重试的初始化"""
        for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
            try:
                await self._initialize_connections()
                self._is_healthy = True
                self._failed_attempts = 0

                # 启动健康检查任务
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                logger.info("Redis 健康检查任务已启动")

                return
            except Exception as e:
                self._failed_attempts += 1
                logger.warning(
                    f"Redis 连接尝试 {attempt + 1}/{self.MAX_RECONNECT_ATTEMPTS} 失败: {e}"
                )
                if attempt < self.MAX_RECONNECT_ATTEMPTS - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避

        # 所有尝试都失败
        logger.error("Redis 连接失败，已禁用 Redis 功能")
        self.enabled = False
        self._is_healthy = False

    async def _initialize_connections(self):
        """初始化 Redis 连接"""
        # Create async connection pool
        self.pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
            max_connections=50,
            socket_keepalive=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,  # Redis 连接池健康检查
        )
        self.client = AsyncRedis(connection_pool=self.pool)

        # Create sync connection pool for blocking operations
        self.sync_pool = SyncConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
            max_connections=50,
            socket_keepalive=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        self.sync_client = SyncRedis(connection_pool=self.sync_pool)

        # 测试连接
        await asyncio.wait_for(self.client.ping(), timeout=self.DEFAULT_TIMEOUT)

        logger.info(
            f"Redis connected: {settings.redis_host}:{settings.redis_port}"
            f" (prefix={self.prefix}, ttl={settings.redis_ttl}s)"
        )

    def _key(self, key: str) -> str:
        """Generate Redis key with prefix"""
        return f"{self.prefix}{key}"

    # ============ 同步方法（用于UserService等同步上下文）============

    def _ensure_sync_client(self):
        """确保同步客户端已初始化（用于同步上下文）"""
        if not self.enabled:
            return False
        if self.sync_client is not None:
            return True

        try:
            # 创建同步连接池
            self.sync_pool = SyncConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,
                socket_timeout=self.DEFAULT_TIMEOUT,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self.sync_client = SyncRedis(connection_pool=self.sync_pool)
            self._initialized = True
            self._is_healthy = True
            logger.info("Redis sync client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Redis sync client: {e}")
            self._is_healthy = False
            return False

    def get_sync(self, key: str) -> Optional[str]:
        """同步获取值"""
        if not self.enabled:
            return None
        self._ensure_sync_client()
        if not self.sync_client:
            return None
        try:
            return self.sync_client.get(self._key(key))
        except Exception as e:
            logger.error(f"Redis get_sync error: {e}")
            return None

    def set_sync(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """同步设置值"""
        if not self.enabled:
            return False
        self._ensure_sync_client()
        if not self.sync_client:
            return False
        try:
            ttl = ttl or settings.redis_ttl
            return self.sync_client.setex(self._key(key), ttl, value)
        except Exception as e:
            logger.error(f"Redis set_sync error: {e}")
            return False

    def get_json_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """同步获取JSON值"""
        value = self.get_sync(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in Redis key: {key}")
        return None

    def set_json_sync(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """同步设置JSON值"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return self.set_sync(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Redis set_json_sync error: {e}")
            return False

    def exists_sync(self, key: str) -> bool:
        """同步检查键是否存在"""
        if not self.enabled:
            return False
        self._ensure_sync_client()
        if not self.sync_client:
            return False
        try:
            return self.sync_client.exists(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists_sync error: {e}")
            return False

    def delete_sync(self, key: str) -> bool:
        """同步删除键"""
        if not self.enabled:
            return False
        self._ensure_sync_client()
        if not self.sync_client:
            return False
        try:
            return self.sync_client.delete(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Redis delete_sync error: {e}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.enabled:
            return None
        await self._ensure_initialized()
        if not self.client:
            return None
        try:
            return await self.client.get(self._key(key))
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL"""
        if not self.enabled:
            return False
        await self._ensure_initialized()
        if not self.client:
            return False
        try:
            ttl = ttl or settings.redis_ttl
            return await self.client.setex(self._key(key), ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.enabled or not self.client:
            return False
        try:
            return await self.client.delete(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.enabled or not self.client:
            return False
        try:
            return await self.client.exists(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for key"""
        if not self.enabled or not self.client:
            return False
        try:
            return await self.client.expire(self._key(key), ttl)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    async def incr(self, key: str) -> int:
        """Increment counter"""
        if not self.enabled or not self.client:
            return 0
        try:
            return await self.client.incr(self._key(key))
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0

    async def expire_counter(self, key: str, ttl: int) -> bool:
        """Expire counter only on first increment (atomic)"""
        if not self.enabled or not self.client:
            return False
        try:
            # Only set expiry if key doesn't have one
            return await self.client.expire(self._key(key), ttl)
        except Exception as e:
            logger.error(f"Redis expire_counter error: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in Redis key: {key}")
        return None

    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set JSON value in Redis"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Redis set_json error: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def _health_check_loop(self):
        """健康检查循环"""
        while self.enabled:
            try:
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
                is_healthy = await self.health_check()

                if not is_healthy and self._is_healthy:
                    # 从健康变为不健康，尝试重连
                    logger.warning("Redis 连接断开，尝试重新连接...")
                    await self._reconnect()

                self._last_health_check = datetime.now()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e}")

    async def _reconnect(self):
        """重新连接 Redis"""
        logger.info("开始 Redis 重连...")
        self._is_healthy = False

        # 关闭旧连接
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()
        except Exception as e:
            logger.warning(f"关闭旧连接时出错: {e}")

        # 重新初始化
        await self._initialize_with_retry()

    async def health_check(self) -> bool:
        """
        检查 Redis 健康状态

        Returns:
            bool: 是否健康
        """
        if not self.enabled:
            return False

        # 尝试初始化（如果还未初始化）
        await self._ensure_initialized()

        if not self.client:
            return False

        try:
            async with asyncio.timeout(self.DEFAULT_TIMEOUT):
                result = await self.client.ping()
                self._is_healthy = result
                return result
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            self._is_healthy = False
            return False

    def is_enabled(self) -> bool:
        """Check if Redis is enabled"""
        return self.enabled

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        return self._is_healthy and self.enabled

    async def ensure_connection(self) -> bool:
        """
        确保 Redis 连接可用

        如果连接不可用，尝试重新连接

        Returns:
            bool: 连接是否可用
        """
        if not self.enabled:
            return False

        if self._is_healthy:
            return True

        # 尝试重新连接
        await self._reconnect()
        return self._is_healthy


# Global Redis service instance
redis_service = RedisService()
