"""User service for managing user state and profiles"""

import logging
from typing import Dict, Any, Optional
from src.models.user_state import UserState
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user data and profiles"""

    def __init__(self):
        """Initialize user service"""
        self.user_states: Dict[str, UserState] = {}
        self.user_profiles: Dict[str, UserProfile] = {}

    def get_user_state(self, user_id: str) -> UserState:
        """Get user state, create if not exists"""
        if user_id not in self.user_states:
            self.user_states[user_id] = UserState(user_id)
            logger.info(f"Created new user state for user: {user_id}")

        return self.user_states[user_id]

    def get_user_profile(self, account_id: str) -> UserProfile:
        """
        获取用户信息档案，如果不存在则创建新的

        Args:
            account_id: 用户账号ID

        Returns:
            UserProfile: 用户信息档案
        """
        if account_id not in self.user_profiles:
            self.user_profiles[account_id] = UserProfile(account_id=account_id)
            logger.info(f"Created new user profile for account: {account_id}")

        return self.user_profiles[account_id]

    def update_user_profile_field(self, account_id: str, field_name: str, value: Any) -> bool:
        """
        更新用户信息字段

        Args:
            account_id: 用户账号ID
            field_name: 字段名称
            value: 字段值

        Returns:
            bool: 是否更新成功
        """
        profile = self.get_user_profile(account_id)
        success = profile.update_field(field_name, value)

        if success:
            logger.info(f"Updated {field_name} for user {account_id}: {value}")

        return success

    def get_user_profile_dict(self, account_id: str) -> Dict[str, Any]:
        """
        获取用户信息的字典形式

        Args:
            account_id: 用户账号ID

        Returns:
            Dict[str, Any]: 用户信息字典
        """
        profile = self.get_user_profile(account_id)
        return profile.to_dict()

    def get_user_greeting(self, account_id: str) -> str:
        """
        根据用户信息生成合适的称呼

        Args:
            account_id: 用户账号ID

        Returns:
            str: 称呼（如"您"、"小姐姐"、"小哥哥"等）
        """
        profile = self.get_user_profile(account_id)
        return profile.get_greeting()

    def get_collection_progress(self, account_id: str) -> float:
        """
        获取用户信息收集进度

        Args:
            account_id: 用户账号ID

        Returns:
            float: 收集进度百分比 (0.0 - 1.0)
        """
        profile = self.get_user_profile(account_id)
        return profile.get_progress()

    def get_next_field_to_collect(self, account_id: str) -> Optional[str]:
        """
        获取下一个需要收集的字段

        Args:
            account_id: 用户账号ID

        Returns:
            Optional[str]: 下一个要收集的字段名
        """
        profile = self.get_user_profile(account_id)
        return profile.get_next_field_to_collect()

    def get_missing_fields(self, account_id: str) -> list:
        """
        获取未收集的字段列表

        Args:
            account_id: 用户账号ID

        Returns:
            list: 未收集的字段名列表
        """
        profile = self.get_user_profile(account_id)
        return profile.get_missing_fields()

    def is_field_error_limit_reached(self, account_id: str, field_name: str, max_errors: int = 2) -> bool:
        """
        检查字段错误次数是否达到限制

        Args:
            account_id: 用户账号ID
            field_name: 字段名
            max_errors: 最大错误次数

        Returns:
            bool: 是否达到错误限制
        """
        profile = self.get_user_profile(account_id)
        return profile.is_field_error_limit_reached(field_name, max_errors)

    def reset_field_error_count(self, account_id: str, field_name: str) -> None:
        """
        重置字段错误计数

        Args:
            account_id: 用户账号ID
            field_name: 字段名
        """
        profile = self.get_user_profile(account_id)
        profile.reset_error_count(field_name)

    def update_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update user preference"""
        user_state = self.get_user_state(user_id)
        user_state.update_preference(key, value)
        logger.info(f"Updated preference {key} for user: {user_id}")

    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference"""
        user_state = self.get_user_state(user_id)
        return user_state.get_preference(key, default)

    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user insights"""
        user_state = self.get_user_state(user_id)
        return user_state.get_user_insights()

    def get_conversation_context(self, user_id: str, lookback: int = 5) -> Dict[str, Any]:
        """Get conversation context for user"""
        user_state = self.get_user_state(user_id)
        return user_state.get_conversation_context(lookback)

    def record_interaction(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record user interaction"""
        user_state = self.get_user_state(user_id)
        user_state.record_interaction(user_message, assistant_response, metadata)

    def get_conversation_history(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get conversation history"""
        user_state = self.get_user_state(user_id)
        history = user_state.conversation_history[offset:offset + limit]

        return {
            "user_id": user_id,
            "conversations": history,
            "total_count": len(user_state.conversation_history),
            "limit": limit,
            "offset": offset
        }

    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get conversation summary"""
        user_state = self.get_user_state(user_id)
        return user_state.get_conversation_summary()

    def is_new_user(self, user_id: str, threshold_hours: int = 24) -> bool:
        """Check if user is new"""
        user_state = self.get_user_state(user_id)
        return user_state.is_new_user(threshold_hours)

    def is_active_user(self, user_id: str, threshold_hours: int = 168) -> bool:
        """Check if user is active"""
        user_state = self.get_user_state(user_id)
        return user_state.is_active_user(threshold_hours)

    def reset_conversation(self, user_id: str) -> None:
        """Reset user conversation"""
        if user_id in self.user_states:
            self.user_states[user_id].reset_conversation()
            logger.info(f"Reset conversation for user: {user_id}")

    def get_all_user_ids(self) -> list:
        """Get all user IDs"""
        return list(self.user_states.keys())

    def get_all_profile_ids(self) -> list:
        """获取所有用户档案ID"""
        return list(self.user_profiles.keys())

    def get_active_users_count(self, threshold_hours: int = 168) -> int:
        """Get count of active users"""
        count = 0
        for user_state in self.user_states.values():
            if user_state.is_active_user(threshold_hours):
                count += 1
        return count

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        total_users = len(self.user_states)
        active_users = self.get_active_users_count()

        # Calculate total dialogs
        total_dialogs = sum(
            user_state.dialog_count
            for user_state in self.user_states.values()
        )

        # Get most active users
        active_user_ids = [
            user_id for user_id, user_state in self.user_states.items()
            if user_state.is_active_user()
        ]

        # Profile statistics
        profile_stats = {
            "total_profiles": len(self.user_profiles),
            "completed_profiles": sum(
                1 for profile in self.user_profiles.values()
                if profile.get_progress() >= 0.8
            ),
            "average_progress": 0
        }

        if self.user_profiles:
            total_progress = sum(profile.get_progress() for profile in self.user_profiles.values())
            profile_stats["average_progress"] = round(total_progress / len(self.user_profiles) * 100, 2)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_dialogs": total_dialogs,
            "average_dialogs_per_user": total_dialogs / total_users if total_users > 0 else 0,
            "active_user_ids": active_user_ids,
            "profile_statistics": profile_stats
        }

    def remove_inactive_users(self, threshold_hours: int = 336) -> int:
        """Remove inactive users"""
        removed_count = 0
        user_ids_to_remove = []

        for user_id, user_state in self.user_states.items():
            if not user_state.is_active_user(threshold_hours):
                user_ids_to_remove.append(user_id)
                removed_count += 1

        for user_id in user_ids_to_remove:
            del self.user_states[user_id]
            if user_id in self.user_profiles:
                del self.user_profiles[user_id]

        if removed_count > 0:
            logger.info(f"Removed {removed_count} inactive users")

        return removed_count

    def export_user_state(self, user_id: str) -> Dict[str, Any]:
        """Export user state for persistence"""
        if user_id in self.user_states:
            return self.user_states[user_id].export_state()
        return {}

    def import_user_state(self, user_state_data: Dict[str, Any]) -> None:
        """Import user state from data"""
        from src.models.user_state import UserState
        user_state = UserState.from_dict(user_state_data)
        self.user_states[user_state.user_id] = user_state

    def cleanup_expired_states(self, max_age_hours: int = 720) -> int:
        """Clean up expired user states"""
        import datetime
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
        expired_users = []

        for user_id, user_state in self.user_states.items():
            if user_state.last_interaction and user_state.last_interaction < cutoff_time:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.user_states[user_id]
            if user_id in self.user_profiles:
                del self.user_profiles[user_id]

        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user states")

        return len(expired_users)

    # New methods for info collection

    def get_next_field_to_collect(self, account_id: str) -> Optional[str]:
        """
        获取下一个需要收集的字段

        Args:
            account_id: 用户账号ID

        Returns:
            Optional[str]: 下一个要收集的字段名
        """
        profile = self.get_user_profile(account_id)
        return profile.get_next_field_to_collect()

    def get_missing_fields(self, account_id: str) -> list:
        """
        获取未收集的字段列表

        Args:
            account_id: 用户账号ID

        Returns:
            list: 未收集的字段名列表
        """
        profile = self.get_user_profile(account_id)
        return profile.get_missing_fields()

    def is_field_error_limit_reached(self, account_id: str, field_name: str, max_errors: int = 2) -> bool:
        """
        检查字段错误次数是否达到限制

        Args:
            account_id: 用户账号ID
            field_name: 字段名
            max_errors: 最大错误次数

        Returns:
            bool: 是否达到错误限制
        """
        profile = self.get_user_profile(account_id)
        return profile.is_field_error_limit_reached(field_name, max_errors)

    def reset_field_error_count(self, account_id: str, field_name: str) -> None:
        """
        重置字段错误计数

        Args:
            account_id: 用户账号ID
            field_name: 字段名
        """
        profile = self.get_user_profile(account_id)
        profile.reset_error_count(field_name)
