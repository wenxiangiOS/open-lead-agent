"""
Redis 存储实现

使用 Redis 作为主要存储后端，支持高并发
"""

import logging
from typing import Optional, Dict, Any, List

from ..base import IUserProfileRepository, IUserStateRepository
from ...services.redis_service import redis_service

logger = logging.getLogger(__name__)


class RedisUserProfileRepository(IUserProfileRepository):
    """Redis 用户档案存储"""

    def __init__(self, ttl: int = 86400):
        """
        初始化 Redis 用户档案存储

        Args:
            ttl: 数据过期时间（秒），默认24小时
        """
        self.ttl = ttl
        self.prefix = "user_profile"

    def _make_key(self, account_id: str) -> str:
        """生成 Redis 键"""
        return f"{self.prefix}:{account_id}"

    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        if not redis_service.is_enabled():
            return None

        try:
            data = redis_service.get_json_sync(self._make_key(account_id))
            return data
        except Exception as e:
            logger.error(f"Redis get user_profile error: {e}")
            return None

    def save(self, account_id: str, profile_data: Dict[str, Any]) -> bool:
        """保存用户档案"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.set_json_sync(
                self._make_key(account_id),
                profile_data,
                ttl=self.ttl
            )
        except Exception as e:
            logger.error(f"Redis save user_profile error: {e}")
            return False

    def delete(self, account_id: str) -> bool:
        """删除用户档案"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.delete_sync(self._make_key(account_id))
        except Exception as e:
            logger.error(f"Redis delete user_profile error: {e}")
            return False

    def exists(self, account_id: str) -> bool:
        """检查用户档案是否存在"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.exists_sync(self._make_key(account_id))
        except Exception as e:
            logger.error(f"Redis exists user_profile error: {e}")
            return False

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        if not redis_service.is_enabled():
            return []

        try:
            pattern = f"{self.prefix}:*"
            keys = redis_service.keys_sync(pattern)
            # 移除前缀，只返回 account_id
            return [key.split(':')[-1] for key in keys]
        except Exception as e:
            logger.error(f"Redis get_all_ids error: {e}")
            return []

    def is_healthy(self) -> bool:
        """健康检查"""
        return redis_service.is_enabled()


class RedisUserStateRepository(IUserStateRepository):
    """Redis 用户状态存储"""

    def __init__(self, ttl: int = 86400):
        """
        初始化 Redis 用户状态存储

        Args:
            ttl: 数据过期时间（秒），默认24小时
        """
        self.ttl = ttl
        self.prefix = "user_state"

    def _make_key(self, user_id: str) -> str:
        """生成 Redis 键"""
        return f"{self.prefix}:{user_id}"

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        if not redis_service.is_enabled():
            return None

        try:
            data = redis_service.get_json_sync(self._make_key(user_id))
            return data
        except Exception as e:
            logger.error(f"Redis get user_state error: {e}")
            return None

    def save(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """保存用户状态"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.set_json_sync(
                self._make_key(user_id),
                state_data,
                ttl=self.ttl
            )
        except Exception as e:
            logger.error(f"Redis save user_state error: {e}")
            return False

    def delete(self, user_id: str) -> bool:
        """删除用户状态"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.delete_sync(self._make_key(user_id))
        except Exception as e:
            logger.error(f"Redis delete user_state error: {e}")
            return False

    def exists(self, user_id: str) -> bool:
        """检查用户状态是否存在"""
        if not redis_service.is_enabled():
            return False

        try:
            return redis_service.exists_sync(self._make_key(user_id))
        except Exception as e:
            logger.error(f"Redis exists user_state error: {e}")
            return False

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        if not redis_service.is_enabled():
            return []

        try:
            pattern = f"{self.prefix}:*"
            keys = redis_service.keys_sync(pattern)
            # 移除前缀，只返回 user_id
            return [key.split(':')[-1] for key in keys]
        except Exception as e:
            logger.error(f"Redis get_all_ids error: {e}")
            return []

    def is_healthy(self) -> bool:
        """健康检查"""
        return redis_service.is_enabled()
