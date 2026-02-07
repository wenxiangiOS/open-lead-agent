"""
混合存储实现

自动切换 Redis 和内存存储，提供高可用性
"""

import logging
from typing import Optional, Dict, Any, List

from ..base import IUserProfileRepository, IUserStateRepository

logger = logging.getLogger(__name__)


class HybridUserProfileRepository(IUserProfileRepository):
    """
    混合用户档案存储

    优先使用 Redis，失败时自动降级到内存存储
    """

    def __init__(self, redis_repo: IUserProfileRepository, memory_repo: IUserProfileRepository):
        """
        初始化混合存储

        Args:
            redis_repo: Redis 存储实现
            memory_repo: 内存存储实现
        """
        self.redis_repo = redis_repo
        self.memory_repo = memory_repo

    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案（优先 Redis）"""
        # 先尝试从 Redis 获取
        if self.redis_repo.is_healthy():
            data = self.redis_repo.get(account_id)
            if data is not None:
                # 同步到内存缓存
                self.memory_repo.save(account_id, data)
                return data
            else:
                # Redis 中没有，尝试从内存获取
                return self.memory_repo.get(account_id)

        # Redis 不可用，从内存获取
        return self.memory_repo.get(account_id)

    def save(self, account_id: str, profile_data: Dict[str, Any]) -> bool:
        """保存用户档案（同时保存到 Redis 和内存）"""
        success = True

        # 尝试保存到 Redis
        if self.redis_repo.is_healthy():
            if not self.redis_repo.save(account_id, profile_data):
                logger.warning(f"Redis save failed for user_profile:{account_id}, using memory only")
                success = False

        # 同时保存到内存
        self.memory_repo.save(account_id, profile_data)
        return success

    def delete(self, account_id: str) -> bool:
        """删除用户档案（同时删除 Redis 和内存）"""
        success = True

        # 尝试从 Redis 删除
        if self.redis_repo.is_healthy():
            if not self.redis_repo.delete(account_id):
                success = False

        # 从内存删除
        self.memory_repo.delete(account_id)
        return success

    def exists(self, account_id: str) -> bool:
        """检查用户档案是否存在"""
        # 先检查 Redis
        if self.redis_repo.is_healthy():
            if self.redis_repo.exists(account_id):
                return True

        # Redis 中不存在或不可用，检查内存
        return self.memory_repo.exists(account_id)

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        # 优先返回 Redis 的 ID 列表
        if self.redis_repo.is_healthy():
            redis_ids = self.redis_repo.get_all_ids()
            # 合并内存中的 ID（去重）
            memory_ids = set(self.memory_repo.get_all_ids())
            all_ids = set(redis_ids) | memory_ids
            return list(all_ids)

        return self.memory_repo.get_all_ids()

    def is_healthy(self) -> bool:
        """健康检查（Redis 或内存任一可用即健康）"""
        return self.redis_repo.is_healthy() or self.memory_repo.is_healthy()


class HybridUserStateRepository(IUserStateRepository):
    """
    混合用户状态存储

    优先使用 Redis，失败时自动降级到内存存储
    """

    def __init__(self, redis_repo: IUserStateRepository, memory_repo: IUserStateRepository):
        """
        初始化混合存储

        Args:
            redis_repo: Redis 存储实现
            memory_repo: 内存存储实现
        """
        self.redis_repo = redis_repo
        self.memory_repo = memory_repo

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户状态（优先 Redis）"""
        # 先尝试从 Redis 获取
        if self.redis_repo.is_healthy():
            data = self.redis_repo.get(user_id)
            if data is not None:
                # 同步到内存缓存
                self.memory_repo.save(user_id, data)
                return data
            else:
                # Redis 中没有，尝试从内存获取
                return self.memory_repo.get(user_id)

        # Redis 不可用，从内存获取
        return self.memory_repo.get(user_id)

    def save(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """保存用户状态（同时保存到 Redis 和内存）"""
        success = True

        # 尝试保存到 Redis
        if self.redis_repo.is_healthy():
            if not self.redis_repo.save(user_id, state_data):
                logger.warning(f"Redis save failed for user_state:{user_id}, using memory only")
                success = False

        # 同时保存到内存
        self.memory_repo.save(user_id, state_data)
        return success

    def delete(self, user_id: str) -> bool:
        """删除用户状态（同时删除 Redis 和内存）"""
        success = True

        # 尝试从 Redis 删除
        if self.redis_repo.is_healthy():
            if not self.redis_repo.delete(user_id):
                success = False

        # 从内存删除
        self.memory_repo.delete(user_id)
        return success

    def exists(self, user_id: str) -> bool:
        """检查用户状态是否存在"""
        # 先检查 Redis
        if self.redis_repo.is_healthy():
            if self.redis_repo.exists(user_id):
                return True

        # Redis 中不存在或不可用，检查内存
        return self.memory_repo.exists(user_id)

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        # 优先返回 Redis 的 ID 列表
        if self.redis_repo.is_healthy():
            redis_ids = self.redis_repo.get_all_ids()
            # 合并内存中的 ID（去重）
            memory_ids = set(self.memory_repo.get_all_ids())
            all_ids = set(redis_ids) | memory_ids
            return list(all_ids)

        return self.memory_repo.get_all_ids()

    def is_healthy(self) -> bool:
        """健康检查（Redis 或内存任一可用即健康）"""
        return self.redis_repo.is_healthy() or self.memory_repo.is_healthy()
