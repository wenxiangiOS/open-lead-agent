"""
Repository 抽象接口

定义统一的数据访问接口，支持多种存储后端
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class IUserProfileRepository(ABC):
    """用户档案存储接口"""

    @abstractmethod
    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        pass

    @abstractmethod
    def save(self, account_id: str, profile_data: Dict[str, Any]) -> bool:
        """保存用户档案"""
        pass

    @abstractmethod
    def delete(self, account_id: str) -> bool:
        """删除用户档案"""
        pass

    @abstractmethod
    def exists(self, account_id: str) -> bool:
        """检查用户档案是否存在"""
        pass

    @abstractmethod
    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """健康检查"""
        pass


class IUserStateRepository(ABC):
    """用户状态存储接口"""

    @abstractmethod
    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        pass

    @abstractmethod
    def save(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """保存用户状态"""
        pass

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """删除用户状态"""
        pass

    @abstractmethod
    def exists(self, user_id: str) -> bool:
        """检查用户状态是否存在"""
        pass

    @abstractmethod
    def get_all_ids(self) -> List[str]:
        """获取所有用户ID"""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """健康检查"""
        pass
