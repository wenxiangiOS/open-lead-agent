"""
缓存插件

增强的缓存功能
"""

import logging
import hashlib
import json
from typing import Any, Optional, Dict

from src.plugins import Plugin, PluginMetadata, PluginConfig
from src.utils import redis_get, redis_set

logger = logging.getLogger(__name__)


class CachePlugin(Plugin):
    """
    缓存插件

    提供增强的缓存功能：
    - 智能缓存键生成
    - 缓存统计
    - 缓存预热
    """

    metadata = PluginMetadata(
        name="cache",
        version="1.0.0",
        description="增强的缓存功能",
        author="系统",
        dependencies=["logging"],  # 依赖日志插件
        tags=["cache", "performance"],
        priority=20,
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        self._hit_count = 0
        self._miss_count = 0
        self._default_ttl = config.get("default_ttl", 3600) if config else 3600

    async def on_load(self) -> bool:
        """加载插件"""
        logger.info("缓存插件加载成功")
        return True

    async def on_activate(self) -> bool:
        """激活插件"""
        # 注册事件监听器
        self.register_hook("cache.get", self._on_cache_get)
        self.register_hook("cache.set", self._on_cache_set)
        self.register_hook("cache.delete", self._on_cache_delete)

        logger.info("✅ 缓存插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """停用插件"""
        logger.info("缓存插件停用")
        return True

    async def on_unload(self) -> bool:
        """卸载插件"""
        logger.info("缓存插件卸载")
        return True

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def _on_cache_get(self, key: str, **kwargs):
        """缓存获取事件"""
        result = await redis_get(key)
        if result is not None:
            self._hit_count += 1
        else:
            self._miss_count += 1

    async def _on_cache_set(self, key: str, value: Any, ttl: Optional[int] = None, **kwargs):
        """缓存设置事件"""
        ttl = ttl or self._default_ttl
        await redis_set(key, value, ttl)

    async def _on_cache_delete(self, key: str, **kwargs):
        """缓存删除事件"""
        from src.utils import redis_delete
        await redis_delete(key)

    # ========================================================================
    # 插件功能
    # ========================================================================

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键
        """
        # 生成参数哈希
        params_hash = hashlib.md5(
            json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True).encode()
        ).hexdigest()[:8]

        return f"{prefix}:{params_hash}"

    async def get_cached(self, key: str, default=None):
        """获取缓存"""
        return await redis_get(key, default=default)

    async def set_cached(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        ttl = ttl or self._default_ttl
        return await redis_set(key, value, ttl)

    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或设置缓存

        Args:
            key: 缓存键
            factory: 值工厂函数（缓存未命中时调用）
            ttl: 过期时间

        Returns:
            缓存值或工厂函数返回值
        """
        value = await self.get_cached(key)
        if value is not None:
            return value

        # 缓存未命中，调用工厂函数
        if callable(factory):
            value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
            await self.set_cached(key, value, ttl)
            return value

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0

        return {
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": round(hit_rate * 100, 2),
            "total_requests": total
        }

    def clear_stats(self):
        """清空统计"""
        self._hit_count = 0
        self._miss_count = 0
