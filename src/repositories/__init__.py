"""
数据访问层（Repository Pattern）

将存储逻辑从业务逻辑中抽离，支持多种存储后端
"""

from .base import IUserProfileRepository, IUserStateRepository
from .implementations.redis_storage import RedisUserProfileRepository, RedisUserStateRepository
from .implementations.memory_storage import MemoryUserProfileRepository, MemoryUserStateRepository
from .implementations.hybrid_storage import HybridUserProfileRepository, HybridUserStateRepository
from .storage_factory import StorageFactory, get_storage_factory, reset_storage_factory

__all__ = [
    # 抽象接口
    'IUserProfileRepository',
    'IUserStateRepository',
    # Redis 实现
    'RedisUserProfileRepository',
    'RedisUserStateRepository',
    # 内存实现
    'MemoryUserProfileRepository',
    'MemoryUserStateRepository',
    # 混合实现
    'HybridUserProfileRepository',
    'HybridUserStateRepository',
    # 存储工厂
    'StorageFactory',
    'get_storage_factory',
    'reset_storage_factory',
]
