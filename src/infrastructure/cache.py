"""
缓存策略模块

提供多种缓存实现：
1. 内存缓存（LRU）
2. Redis 缓存
3. 缓存装饰器
"""

import asyncio
import functools
import hashlib
import json
import logging
from typing import Optional, Any, Callable, Dict, Tuple
from datetime import timedelta
from collections import OrderedDict

from src.services.data.redis_service import redis_service

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    内存缓存（LRU 淘汰策略）

    适用于：
    - 提示词缓存
    - 配置缓存
    - 热点数据
    """

    def __init__(self, max_size: int = 128, ttl: int = 3600):
        """
        初始化内存缓存

        Args:
            max_size: 最大缓存条目数
            ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = asyncio.Lock()

    def _generate_key(self, key: Any) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return key
        # 对于复杂对象，使用哈希
        key_str = json.dumps(key, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(self, key: Any) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        cache_key = self._generate_key(key)

        async with self._lock:
            if cache_key not in self._cache:
                return None

            value, timestamp = self._cache[cache_key]

            # 检查是否过期
            if asyncio.get_event_loop().time() - timestamp > self.ttl:
                del self._cache[cache_key]
                return None

            # LRU：移到末尾
            self._cache.move_to_end(cache_key)
            return value

    async def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认使用配置值
        """
        cache_key = self._generate_key(key)
        ttl = ttl or self.ttl

        async with self._lock:
            # 检查容量
            if len(self._cache) >= self.max_size:
                # 删除最旧的项
                self._cache.popitem(last=False)

            # 存储值和时间戳
            self._cache[cache_key] = (value, asyncio.get_event_loop().time())

    async def delete(self, key: Any) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        cache_key = self._generate_key(key)

        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class RedisCache:
    """
    Redis 缓存

    适用于：
    - 分布式缓存
    - 持久化缓存
    - 大容量缓存
    """

    def __init__(self, ttl: int = 3600):
        """
        初始化 Redis 缓存

        Args:
            ttl: 默认过期时间（秒）
        """
        self.ttl = ttl
        self.prefix = "cache:"

    def _generate_key(self, key: Any) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return f"{self.prefix}{key}"
        # 对于复杂对象，使用哈希
        key_str = json.dumps(key, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{self.prefix}{key_hash}"

    async def get(self, key: Any) -> Optional[Any]:
        """获取缓存"""
        if not redis_service.is_enabled():
            return None

        try:
            data = await redis_service.get_json(self._generate_key(key))
            return data
        except Exception as e:
            logger.error(f"Redis缓存获取失败: {e}")
            return None

    async def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if not redis_service.is_enabled():
            return False

        try:
            ttl = ttl or self.ttl
            return await redis_service.set_json(
                self._generate_key(key),
                value,
                ttl=ttl
            )
        except Exception as e:
            logger.error(f"Redis缓存设置失败: {e}")
            return False

    async def delete(self, key: Any) -> bool:
        """删除缓存"""
        if not redis_service.is_enabled():
            return False

        try:
            return await redis_service.delete(self._generate_key(key))
        except Exception as e:
            logger.error(f"Redis缓存删除失败: {e}")
            return False

    async def clear(self) -> bool:
        """清空所有缓存（需要遍历，谨慎使用）"""
        # Redis 缓存不建议清空所有
        logger.warning("Redis 缓存不支持清空所有操作")
        return False


class HybridCache:
    """
    混合缓存策略

    优先使用内存缓存，Redis 作为后备：
    1. 热点数据 → 内存缓存
    2. 大容量数据 → Redis 缓存
    3. Redis 不可用时 → 仅使用内存
    """

    def __init__(
        self,
        memory_ttl: int = 3600,
        redis_ttl: int = 86400,
        memory_size: int = 256
    ):
        """
        初始化混合缓存

        Args:
            memory_ttl: 内存缓存TTL
            redis_ttl: Redis缓存TTL
            memory_size: 内存缓存大小
        """
        self.memory_cache = MemoryCache(max_size=memory_size, ttl=memory_ttl)
        self.redis_cache = RedisCache(ttl=redis_ttl)

    async def get(self, key: Any, use_redis: bool = False) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键
            use_redis: 是否使用Redis缓存

        Returns:
            缓存值
        """
        # 优先从内存获取
        value = await self.memory_cache.get(key)
        if value is not None:
            return value

        # 从Redis获取
        if use_redis or not redis_service.is_healthy():
            value = await self.redis_cache.get(key)
            if value is not None:
                # 回填到内存缓存
                await self.memory_cache.set(key, value)
            return value

        return None

    async def set(
        self,
        key: Any,
        value: Any,
        use_redis: bool = False,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            use_redis: 是否同时存储到Redis
            ttl: 过期时间
        """
        # 存储到内存
        await self.memory_cache.set(key, value, ttl)

        # 可选：存储到Redis
        if use_redis and redis_service.is_healthy():
            await self.redis_cache.set(key, value, ttl)

        return True

    async def delete(self, key: Any) -> bool:
        """删除缓存"""
        # 从内存删除
        await self.memory_cache.delete(key)

        # 从Redis删除
        if redis_service.is_enabled():
            await self.redis_cache.delete(key)

        return True


# ============ 缓存装饰器 ============

def cached(
    cache: Any,
    key_func: Optional[Callable] = None,
    ttl: Optional[int] = None
):
    """
    缓存装饰器

    Args:
        cache: 缓存实例
        key_func: 生成缓存键的函数
        ttl: 过期时间

    Usage:
        @cached(memory_cache)
        async def get_prompt(user_id: str):
            return await load_prompt(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))

            # 尝试获取缓存
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# ============ 预配置缓存实例 ============

# 提示词缓存
prompt_cache = MemoryCache(max_size=64, ttl=3600)

# 用户数据缓存
user_cache = MemoryCache(max_size=256, ttl=300)

# 混合缓存
hybrid_cache = HybridCache()
