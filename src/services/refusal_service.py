"""
拒绝检测服务

管理用户拒绝行为的状态追踪
"""

import logging
import threading
from typing import Dict, Any

from src.utils.validators import RefusalDetector

logger = logging.getLogger(__name__)


class RefusalService:
    """
    拒绝检测服务

    职责：
    1. 检测用户是否拒绝
    2. 记录拒绝次数
    3. 检查是否达到拒绝上限
    """

    def __init__(self, max_refusals: int = 2):
        """
        初始化拒绝服务

        Args:
            max_refusals: 最大拒绝次数
        """
        self.max_refusals = max_refusals
        self._refusal_state: Dict[str, int] = {}
        self._lock = threading.RLock()

    def is_refusing(self, text: str) -> bool:
        """
        检测文本是否包含拒绝内容

        Args:
            text: 用户输入

        Returns:
            bool: 是否拒绝
        """
        return RefusalDetector.is_refusing(text)

    def record_refusal(self, account_id: str, field: str = "contact") -> int:
        """
        记录用户拒绝次数

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            int: 当前拒绝次数
        """
        key = f"{account_id}_{field}_refusal"

        with self._lock:
            self._refusal_state[key] = self._refusal_state.get(key, 0) + 1
            count = self._refusal_state[key]
            logger.info(f"[拒绝记录] {account_id} {field} 拒绝次数: {count}")
            return count

    def get_refusal_count(self, account_id: str, field: str = "contact") -> int:
        """
        获取拒绝次数

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            int: 拒绝次数
        """
        key = f"{account_id}_{field}_refusal"
        return self._refusal_state.get(key, 0)

    def has_reached_limit(self, account_id: str, field: str = "contact") -> bool:
        """
        检查是否达到拒绝上限

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            bool: 是否达到上限
        """
        return self.get_refusal_count(account_id, field) >= self.max_refusals

    def reset_refusal_count(self, account_id: str, field: str = "contact") -> None:
        """
        重置拒绝次数

        Args:
            account_id: 用户ID
            field: 字段名
        """
        key = f"{account_id}_{field}_refusal"
        with self._lock:
            if key in self._refusal_state:
                del self._refusal_state[key]

    def clear_all(self, account_id: str) -> None:
        """
        清除用户的所有拒绝记录

        Args:
            account_id: 用户ID
        """
        with self._lock:
            keys_to_delete = [k for k in self._refusal_state if k.startswith(f"{account_id}_")]
            for key in keys_to_delete:
                del self._refusal_state[key]
