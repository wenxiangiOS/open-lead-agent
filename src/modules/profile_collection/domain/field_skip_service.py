"""
字段跳过管理服务

管理用户跳过某些字段的状态
"""

import logging
import threading
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class FieldSkipService:
    """
    字段跳过管理服务

    职责：
    1. 标记字段为跳过
    2. 检查字段是否已跳过
    3. 管理错误计数
    """

    # 所有可收集的字段
    COLLECTIBLE_FIELDS = [
        'last_name', 'sex', 'age', 'height', 'location',
        'marital_status', 'education', 'occupation',
        'monthly_income', 'contact'
    ]

    def __init__(self, max_errors: int = 2):
        """
        初始化字段跳过服务

        Args:
            max_errors: 最大错误次数
        """
        self.max_errors = max_errors
        self._field_state: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _get_key(self, account_id: str, field: str) -> str:
        """生成状态键"""
        return f"{account_id}_{field}"

    def _init_field_state(self, account_id: str, field: str) -> None:
        """初始化字段状态"""
        key = self._get_key(account_id, field)
        if key not in self._field_state:
            self._field_state[key] = {
                'error_count': 0,
                'skipped': False
            }

    def increment_error(self, account_id: str, field: str) -> int:
        """
        增加字段错误计数

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            int: 当前错误计数
        """
        key = self._get_key(account_id, field)
        self._init_field_state(account_id, field)

        with self._lock:
            self._field_state[key]['error_count'] += 1
            error_count = self._field_state[key]['error_count']

            # 达到错误上限，自动跳过
            if error_count >= self.max_errors:
                self._field_state[key]['skipped'] = True
                logger.info(f"[字段跳过] {account_id} {field} 错误{error_count}次，自动跳过")

            return error_count

    def get_error_count(self, account_id: str, field: str) -> int:
        """
        获取字段错误计数

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            int: 错误计数
        """
        key = self._get_key(account_id, field)
        return self._field_state.get(key, {}).get('error_count', 0)

    def skip_field(self, account_id: str, field: str) -> None:
        """
        手动跳过字段

        Args:
            account_id: 用户ID
            field: 字段名
        """
        key = self._get_key(account_id, field)
        self._init_field_state(account_id, field)

        with self._lock:
            self._field_state[key]['skipped'] = True
            logger.info(f"[字段跳过] {account_id} {field} 已标记跳过")

    def is_field_skipped(self, account_id: str, field: str) -> bool:
        """
        检查字段是否已跳过

        Args:
            account_id: 用户ID
            field: 字段名

        Returns:
            bool: 是否已跳过
        """
        key = self._get_key(account_id, field)
        return self._field_state.get(key, {}).get('skipped', False)

    def get_skipped_fields(self, account_id: str) -> Set[str]:
        """
        获取用户所有跳过的字段

        Args:
            account_id: 用户ID

        Returns:
            Set[str]: 跳过的字段集合
        """
        skipped = set()
        prefix = f"{account_id}_"

        with self._lock:
            for key, state in self._field_state.items():
                if key.startswith(prefix) and state.get('skipped'):
                    field = key[len(prefix):]
                    skipped.add(field)

        return skipped

    def reset_field(self, account_id: str, field: str) -> None:
        """
        重置字段状态

        Args:
            account_id: 用户ID
            field: 字段名
        """
        key = self._get_key(account_id, field)
        with self._lock:
            if key in self._field_state:
                del self._field_state[key]

    def clear_all(self, account_id: str) -> None:
        """
        清除用户的所有字段状态

        Args:
            account_id: 用户ID
        """
        prefix = f"{account_id}_"
        keys_to_delete = [k for k in self._field_state if k.startswith(prefix)]

        with self._lock:
            for key in keys_to_delete:
                del self._field_state[key]
