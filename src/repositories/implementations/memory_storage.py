"""
内存存储实现

作为 Redis 不可用时的备用存储，或用于开发/测试环境
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..base import IUserProfileRepository, IUserStateRepository

logger = logging.getLogger(__name__)


class MemoryUserProfileRepository(IUserProfileRepository):
    """内存用户档案存储"""

    def __init__(self, ttl: int = 86400):
        """
        初始化内存用户档案存储

        Args:
            ttl: 数据过期时间（秒），默认24小时
        """
        self.ttl = ttl
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}

    def _clean_expired(self):
        """清理过期数据"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self._expiry.items()
            if expiry and expiry < now
        ]
        for key in expired_keys:
            del self._storage[key]
            del self._expiry[key]

    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        self._clean_expired()
        return self._storage.get(account_id)

    def save(self, account_id: str, profile_data: Dict[str, Any]) -> bool:
        """保存用户档案"""
        self._storage[account_id] = profile_data
        # 设置过期时间
        if self.ttl > 0:
            self._expiry[account_id] = datetime.now() + timedelta(seconds=self.ttl)
        return True

    def delete(self, account_id: str) -> bool:
        """删除用户档案"""
        self._storage.pop(account_id, None)
        self._expiry.pop(account_id, None)
        return True

    def exists(self, account_id: str) -> bool:
        """检查用户档案是否存在"""
        self._clean_expired()
        return account_id in self._storage

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        self._clean_expired()
        return list(self._storage.keys())

    def is_healthy(self) -> bool:
        """健康检查（内存存储总是健康的）"""
        return True


class MemoryUserStateRepository(IUserStateRepository):
    """内存用户状态存储"""

    def __init__(self, ttl: int = 86400):
        """
        初始化内存用户状态存储

        Args:
            ttl: 数据过期时间（秒），默认24小时
        """
        self.ttl = ttl
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}

    def _clean_expired(self):
        """清理过期数据"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self._expiry.items()
            if expiry and expiry < now
        ]
        for key in expired_keys:
            del self._storage[key]
            del self._expiry[key]

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        self._clean_expired()
        return self._storage.get(user_id)

    def save(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """保存用户状态"""
        self._storage[user_id] = state_data
        # 设置过期时间
        if self.ttl > 0:
            self._expiry[user_id] = datetime.now() + timedelta(seconds=self.ttl)
        return True

    def delete(self, user_id: str) -> bool:
        """删除用户状态"""
        self._storage.pop(user_id, None)
        self._expiry.pop(user_id, None)
        return True

    def exists(self, user_id: str) -> bool:
        """检查用户状态是否存在"""
        self._clean_expired()
        return user_id in self._storage

    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        self._clean_expired()
        return list(self._storage.keys())

    def is_healthy(self) -> bool:
        """健康检查（内存存储总是健康的）"""
        return True
