"""
Redis 服务优化

统一同步和异步调用，消除重复代码
"""

import asyncio
import logging
from typing import Optional, Any, Dict, Callable, TypeVar, Union
from functools import wraps

from src.services.redis_service import redis_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RedisOperation:
    """
    Redis 操作包装器

    自动处理同步/异步调用，支持降级策略
    """

    def __init__(self, sync_fallback: bool = True):
        """
        初始化操作包装器

        Args:
            sync_fallback: Redis 不可用时是否降级到内存
        """
        self.sync_fallback = sync_fallback
        self._memory_cache: Dict[str, Any] = {}

    async def execute(
        self,
        operation: str,
        key: str,
        *args,
        default: Any = None,
        **kwargs
    ) -> Any:
        """
        执行 Redis 操作

        Args:
            operation: 操作类型 (get/set/delete等)
            key: Redis 键
            *args: 位置参数
            default: Redis 不可用时的默认值
            **kwargs: 关键字参数

        Returns:
            操作结果
        """
        if not redis_service.is_enabled():
            # Redis 未启用，使用内存缓存
            return self._execute_in_memory(operation, key, *args, default=default, **kwargs)

        try:
            # 执行异步操作
            result = await self._execute_async(operation, key, *args, **kwargs)
            return result
        except Exception as e:
            logger.warning(f"Redis 操作失败 ({operation} {key}): {e}")

            # 降级到内存缓存
            if self.sync_fallback:
                return self._execute_in_memory(operation, key, *args, default=default, **kwargs)

            # 返回默认值
            return default

    async def _execute_async(self, operation: str, key: str, *args, **kwargs) -> Any:
        """执行异步 Redis 操作"""
        client = redis_service.client

        if operation == "get":
            return await client.get(key)
        elif operation == "set":
            return await client.set(key, *args, **kwargs)
        elif operation == "delete":
            return await client.delete(key)
        elif operation == "exists":
            return await client.exists(key)
        elif operation == "get_json":
            data = await client.get(key)
            if data:
                import json
                return json.loads(data)
            return None
        elif operation == "set_json":
            import json
            data = json.dumps(args[0])
            ttl = kwargs.get('ttl', redis_service.default_ttl)
            if ttl:
                return await client.setex(key, ttl, data)
            else:
                return await client.set(key, data)
        elif operation == "zadd":
            return await client.zadd(key, *args, **kwargs)
        elif operation == "zrange":
            return await client.zrange(key, *args, **kwargs)
        else:
            raise ValueError(f"不支持的操作: {operation}")

    def _execute_in_memory(self, operation: str, key: str, *args, default: Any = None, **kwargs) -> Any:
        """在内存中执行操作（降级策略）"""
        if operation == "get":
            return self._memory_cache.get(key, default)
        elif operation == "set":
            self._memory_cache[key] = args[0] if args else kwargs.get('value')
            if 'ttl' in kwargs:
                # 简化版内存 TTL，实际需要定时清理
                pass
            return True
        elif operation == "delete":
            self._memory_cache.pop(key, None)
            return True
        elif operation == "exists":
            return key in self._memory_cache
        elif operation == "get_json":
            return self._memory_cache.get(key, default)
        elif operation == "set_json":
            self._memory_cache[key] = args[0] if args else kwargs.get('value')
            return True
        else:
            return default


# ============================================================================
# 便捷函数
# ============================================================================

# 全局 Redis 操作实例
redis_op = RedisOperation()


async def redis_get(key: str, default: Any = None) -> Any:
    """获取 Redis 值（带降级）"""
    return await redis_op.execute("get", key, default=default)


async def redis_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置 Redis 值（带降级）"""
    if ttl:
        return await redis_op.execute("set", key, value, ttl)
    return await redis_op.execute("set", key, value)


async def redis_get_json(key: str, default: Any = None) -> Optional[Any]:
    """获取 JSON 数据（带降级）"""
    return await redis_op.execute("get_json", key, default=default)


async def redis_set_json(key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """设置 JSON 数据（带降级）"""
    return await redis_op.execute("set_json", key, data, ttl=ttl)


async def redis_delete(key: str) -> bool:
    """删除键（带降级）"""
    return await redis_op.execute("delete", key)


async def redis_exists(key: str) -> bool:
    """检查键是否存在（带降级）"""
    return await redis_op.execute("exists", key)


# ============================================================================
# 装饰器
# ============================================================================

def redis_fallback(default_value: Any = None):
    """
    Redis 降级装饰器

    当 Redis 不可用时使用默认值或内存缓存

    Args:
        default_value: Redis 失败时的默认值

    Usage:
        @redis_fallback(default={})
        async def get_user_config(user_id: str):
            return await redis_get_json(f"user:{user_id}")
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Redis 操作失败: {e}，使用降级策略")
                return default_value
        return wrapper
    return decorator


def sync_redis_fallback(default_value: Any = None):
    """
    同步 Redis 降级装饰器

    用于同步函数中的 Redis 调用
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"同步 Redis 操作失败: {e}，使用降级策略")
                return default_value
        return wrapper
    return decorator
