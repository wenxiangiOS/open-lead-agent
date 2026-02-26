"""
统一限流器 - 整合所有限流逻辑

整合了原本分散在多个文件中的限流器：
- src/api/middleware/rate_limit.py (内存限流)
- src/api/middleware/redis_rate_limit.py (Redis限流)
- src/api/middleware/tiered_rate_limit.py (分级限流)
- src/infrastructure/redis_rate_limit.py (另一个Redis限流)
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from src.config.settings import settings
from src.services.redis_service import redis_service

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """限流检查结果"""
    allowed: bool           # 是否允许请求
    limit: int             # 限制数量
    remaining: int         # 剩余数量
    reset_time: float      # 重置时间戳
    tier: str = "default"  # 用户等级
    window: int = 60       # 时间窗口（秒）


class UnifiedRateLimiter:
    """
    统一限流器

    特性：
    1. 支持 Redis 和内存两种存储模式
    2. 支持分级限流（按用户等级）
    3. 滑动窗口算法
    4. 自动降级（Redis 不可用时使用内存）
    """

    def __init__(
        self,
        use_redis: bool = True,
        default_limit: int = 100,
        default_window: int = 60
    ):
        """
        初始化统一限流器

        Args:
            use_redis: 是否使用 Redis
            default_limit: 默认限制数量
            default_window: 默认时间窗口（秒）
        """
        self.use_redis = use_redis and redis_service.is_enabled()
        self.default_limit = default_limit
        self.default_window = default_window

        # 内存模式存储
        self._memory_store: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

        # 分级限流配置
        self.tier_limits = {
            "free": {"limit": 10, "window": 60},
            "basic": {"limit": 50, "window": 60},
            "pro": {"limit": 100, "window": 60},
            "enterprise": {"limit": 1000, "window": 60},
        }

        # 用户等级存储（用户ID -> 等级）
        self._user_tiers: Dict[str, str] = {}

        logger.info(
            f"UnifiedRateLimiter initialized: "
            f"{'Redis mode' if self.use_redis else 'Memory mode'} "
            f"(limit={default_limit}/{default_window}s)"
        )

    async def is_allowed(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> RateLimitResult:
        """
        检查是否允许请求

        Args:
            key: 限流键（用户ID、IP等）
            limit: 限制数量（可选，使用默认值）
            window: 时间窗口（可选，使用默认值）

        Returns:
            RateLimitResult: 限流检查结果
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        if self.use_redis:
            return await self._check_redis(key, limit, window)
        else:
            return await self._check_memory(key, limit, window)

    async def _check_redis(
        self,
        key: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """使用 Redis 检查限流（滑动窗口）"""
        try:
            # 检查 Redis 客户端是否可用
            if not redis_service.client:
                logger.warning("Redis client not available, falling back to memory")
                return await self._check_memory(key, limit, window)

            redis_key = f"ratelimit:{key}"
            current_time = time.time()
            window_start = current_time - window

            # 使用 Lua 脚本保证原子性
            lua_script = """
                local key = KEYS[1]
                local window_start = tonumber(ARGV[1])
                local current_time = tonumber(ARGV[2])
                local limit = tonumber(ARGV[3])

                -- 删除窗口外的记录
                redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

                -- 获取当前窗口内的请求数
                local current_count = redis.call('ZCARD', key)

                -- 检查是否超限
                if current_count < limit then
                    -- 添加当前请求
                    redis.call('ZADD', key, current_time, current_time)
                    -- 设置过期时间
                    redis.call('EXPIRE', key, limit)
                    return {1, limit, limit - current_count - 1}
                else
                    return {0, limit, 0}
                end
            """

            result = await redis_service.client.eval(
                lua_script,
                1,
                redis_key,
                window_start,
                current_time,
                limit
            )

            allowed, limit, remaining = result
            reset_time = current_time + window

            return RateLimitResult(
                allowed=bool(allowed),
                limit=limit,
                remaining=remaining,
                reset_time=reset_time
            )

        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}, falling back to memory")
            return await self._check_memory(key, limit, window)

    async def _check_memory(
        self,
        key: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """使用内存检查限流（滑动窗口）"""
        async with self._lock:
            current_time = time.time()
            window_start = current_time - window

            # 获取该键的请求历史
            requests = self._memory_store[key]

            # 删除窗口外的记录
            requests = [t for t in requests if t > window_start]
            self._memory_store[key] = requests

            # 检查是否超限
            if len(requests) < limit:
                # 添加当前请求
                requests.append(current_time)
                remaining = limit - len(requests)
                reset_time = current_time + window

                return RateLimitResult(
                    allowed=True,
                    limit=limit,
                    remaining=remaining,
                    reset_time=reset_time
                )
            else:
                # 超限
                reset_time = max(requests) + window

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_time=reset_time
                )

    async def check_tiered_limit(
        self,
        user_id: str,
        window: int = 60
    ) -> RateLimitResult:
        """
        检查分级限流（根据用户等级）

        Args:
            user_id: 用户ID
            window: 时间窗口（秒）

        Returns:
            RateLimitResult: 限流检查结果
        """
        # 获取用户等级
        tier = self.get_user_tier(user_id)
        tier_config = self.tier_limits.get(tier, self.tier_limits["free"])

        limit = tier_config["limit"]
        result = await self.is_allowed(user_id, limit, window)

        # 添加等级信息
        result.tier = tier
        result.window = window

        return result

    def set_user_tier(self, user_id: str, tier: str) -> None:
        """设置用户等级"""
        if tier in self.tier_limits:
            self._user_tiers[user_id] = tier
            logger.info(f"Set user tier: {user_id} -> {tier}")

    def get_user_tier(self, user_id: str) -> str:
        """获取用户等级"""
        return self._user_tiers.get(user_id, "free")

    async def reset(self, key: str) -> bool:
        """重置限流计数"""
        try:
            if self.use_redis:
                redis_key = f"ratelimit:{key}"
                await redis_service.delete(redis_key)

            # 同时清除内存缓存
            if key in self._memory_store:
                del self._memory_store[key]

            logger.info(f"Rate limit reset for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")
            return False

    async def get_usage(
        self,
        key: str,
        window: int = 60
    ) -> Dict[str, int]:
        """获取限流使用情况"""
        try:
            if self.use_redis:
                redis_key = f"ratelimit:{key}"
                current_time = time.time()
                window_start = current_time - window

                # 获取窗口内的请求数
                count = await redis_service.client.zcount(
                    redis_key,
                    window_start,
                    current_time
                )

                return {
                    "count": count,
                    "limit": self.default_limit,
                    "remaining": max(0, self.default_limit - count)
                }
            else:
                requests = self._memory_store.get(key, [])
                current_time = time.time()
                window_start = current_time - window

                # 计算窗口内的请求数
                count = sum(1 for t in requests if t > window_start)

                return {
                    "count": count,
                    "limit": self.default_limit,
                    "remaining": max(0, self.default_limit - count)
                }

        except Exception as e:
            logger.error(f"Get rate limit usage error: {e}")
            return {
                "count": 0,
                "limit": self.default_limit,
                "remaining": self.default_limit
            }


# 全局限流器实例
_unified_rate_limiter: Optional[UnifiedRateLimiter] = None


def get_rate_limiter() -> UnifiedRateLimiter:
    """获取全局限流器实例"""
    global _unified_rate_limiter
    if _unified_rate_limiter is None:
        _unified_rate_limiter = UnifiedRateLimiter()
    return _unified_rate_limiter
