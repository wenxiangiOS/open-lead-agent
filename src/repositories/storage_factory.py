"""
存储工厂

根据配置创建合适的存储实现
"""

import logging
from typing import Optional

from .repositories import (
    IUserProfileRepository,
    IUserStateRepository,
    HybridUserProfileRepository,
    HybridUserStateRepository,
    RedisUserProfileRepository,
    RedisUserStateRepository,
    MemoryUserProfileRepository,
    MemoryUserStateRepository
)

logger = logging.getLogger(__name__)


class StorageFactory:
    """
    存储工厂

    根据配置创建存储实例，支持动态切换存储后端
    """

    def __init__(self, redis_enabled: bool = True, ttl: int = 86400):
        """
        初始化存储工厂

        Args:
            redis_enabled: 是否启用 Redis
            ttl: 数据过期时间（秒）
        """
        self.redis_enabled = redis_enabled
        self.ttl = ttl

        # 创建存储实例
        self._redis_profile_repo: Optional[IUserProfileRepository] = None
        self._redis_state_repo: Optional[IUserStateRepository] = None
        self._memory_profile_repo: Optional[IUserProfileRepository] = None
        self._memory_state_repo: Optional[IUserStateRepository] = None

    def get_profile_repository(self) -> IUserProfileRepository:
        """获取用户档案存储实例"""
        # 延迟初始化
        if self._redis_profile_repo is None:
            # 创建 Redis 存储实例
            self._redis_profile_repo = RedisUserProfileRepository(ttl=self.ttl)

        if self._memory_profile_repo is None:
            # 创建内存存储实例
            self._memory_profile_repo = MemoryUserProfileRepository(ttl=self.ttl)

        # 根据 Redis 状态选择存储策略
        if self.redis_enabled and self._redis_profile_repo.is_healthy():
            # Redis 可用，使用混合存储
            return HybridUserProfileRepository(
                redis_repo=self._redis_profile_repo,
                memory_repo=self._memory_profile_repo
            )
        else:
            # Redis 不可用，只使用内存存储
            logger.info("Using memory-only storage for user profiles")
            return self._memory_profile_repo

    def get_state_repository(self) -> IUserStateRepository:
        """获取用户状态存储实例"""
        # 延迟初始化
        if self._redis_state_repo is None:
            # 创建 Redis 存储实例
            self._redis_state_repo = RedisUserStateRepository(ttl=self.ttl)

        if self._memory_state_repo is None:
            # 创建内存存储实例
            self._memory_state_repo = MemoryUserStateRepository(ttl=self.ttl)

        # 根据 Redis 状态选择存储策略
        if self.redis_enabled and self._redis_state_repo.is_healthy():
            # Redis 可用，使用混合存储
            return HybridUserStateRepository(
                redis_repo=self._redis_state_repo,
                memory_repo=self._memory_state_repo
            )
        else:
            # Redis 不可用，只使用内存存储
            logger.info("Using memory-only storage for user states")
            return self._memory_state_repo

    def is_redis_healthy(self) -> bool:
        """检查 Redis 是否健康"""
        if self._redis_profile_repo is None:
            return False
        return self._redis_profile_repo.is_healthy()

    def switch_to_memory_only(self):
        """切换到仅内存模式（Redis 故障时）"""
        logger.warning("Switching to memory-only storage mode")
        self.redis_enabled = False

    def switch_to_hybrid(self):
        """切换回混合模式（Redis 恢复时）"""
        if self._redis_profile_repo and self._redis_profile_repo.is_healthy():
            logger.info("Switching back to hybrid storage mode")
            self.redis_enabled = True


# 全局存储工厂实例（延迟初始化）
_storage_factory: Optional[StorageFactory] = None


def get_storage_factory() -> StorageFactory:
    """获取全局存储工厂实例（单例模式）"""
    global _storage_factory
    if _storage_factory is None:
        from ...config.settings import settings
        _storage_factory = StorageFactory(
            redis_enabled=settings.REDIS_ENABLED,
            ttl=settings.REDIS_TTL
        )
        logger.info(f"StorageFactory initialized: Redis={settings.REDIS_ENABLED}, TTL={settings.REDIS_TTL}")
    return _storage_factory


def reset_storage_factory():
    """重置全局存储工厂（用于测试）"""
    global _storage_factory
    _storage_factory = None
