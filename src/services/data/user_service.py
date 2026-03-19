"""User service for managing user state and profiles"""
#  层级：数据层    核心职责：用户状态和档案管理

import logging
from typing import Dict, Any, Optional
from collections import OrderedDict
from src.models.user_state import UserState
from src.models.user_profile import UserProfile
from src.services.data.redis_service import redis_service
from src.config.settings import settings

logger = logging.getLogger(__name__)


class LRUCache:
    """简单的 LRU 缓存实现，防止内存无限增长"""

    def __init__(self, max_size: int = 1000):
        """
        初始化 LRU 缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，如果存在则移到末尾（最近使用）"""
        if key in self._cache:
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值，如果超过最大容量则删除最旧的项"""
        if key in self._cache:
            # 更新并移到末尾
            self._cache.move_to_end(key)
        self._cache[key] = value

        # 检查容量
        if len(self._cache) > self.max_size:
            # 删除最旧的项（第一个）
            self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def keys(self):
        """获取所有键"""
        return self._cache.keys()

    def values(self):
        """获取所有值"""
        return self._cache.values()

    def items(self):
        """获取所有键值对"""
        return self._cache.items()

    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._cache

    def __getitem__(self, key: str) -> Any:
        """字典风格获取值"""
        if key in self._cache:
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """字典风格设置值"""
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        """字典风格删除值"""
        if key in self._cache:
            del self._cache[key]
        else:
            raise KeyError(key)

    def __len__(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


class UserService:
    """Service for managing user data and profiles (支持Redis和内存)"""

    def __init__(self, cache_max_size: int = 1000):
        """
        Initialize user service

        Args:
            cache_max_size: 内存缓存最大条目数（防止内存泄漏）
        """
        self.use_redis = redis_service.is_enabled()
        logger.info(f"UserService initialized with storage: {'Redis' if self.use_redis else 'Memory'}")

        # 内存缓存（使用 LRU 缓存防止无限增长）
        self._memory_states = LRUCache(max_size=cache_max_size)
        self._memory_profiles = LRUCache(max_size=cache_max_size)

    async def get_user_state(self, user_id: str) -> UserState:
        """Get user state from Redis or memory"""
        if self.use_redis:
            try:
                # 从Redis获取
                data = await redis_service.get_json(f"user_state:{user_id}")
                if data:
                    state = UserState.from_dict(data, user_id)
                    # 保存到内存缓存，避免重复从Redis加载
                    self._memory_states[user_id] = state
                    return state
            except Exception as e:
                logger.error(f"Redis get_user_state error: {e}, using memory fallback")

        # 内存模式或Redis失败
        if user_id not in self._memory_states:
            self._memory_states[user_id] = UserState(user_id)
        return self._memory_states[user_id]

    async def get_user_profile(self, account_id: str) -> UserProfile:
        """Get user profile from Redis or memory"""
        if self.use_redis:
            try:
                # 从Redis获取
                data = await redis_service.get_json(f"user_profile:{account_id}")
                if data:
                    # 从dict转换回UserProfile对象
                    profile = UserProfile.from_dict(data)
                    # 同时保存到内存缓存
                    self._memory_profiles[account_id] = profile
                    # === 调试日志 ===
                    logger.info(f"[用户档案加载] account_id={account_id}, phone_ask_count={profile.phone_ask_count}, wechat_ask_count={profile.wechat_ask_count}, rejected_phone={profile.rejected_phone}")
                    return profile
            except Exception as e:
                logger.error(f"Redis get_user_profile error: {e}, using memory fallback")

        # 内存模式或Redis失败
        if account_id not in self._memory_profiles:
            self._memory_profiles[account_id] = UserProfile(account_id=account_id)

        # 确保返回的是UserProfile对象（可能是dict的情况）
        profile = self._memory_profiles[account_id]
        if isinstance(profile, dict):
            profile = UserProfile.from_dict(profile)
            self._memory_profiles[account_id] = profile

        return profile

    async def save_user_profile(self, account_id: str, profile: UserProfile) -> bool:
        """Save user profile to Redis or memory"""
        profile_dict = profile.to_dict()

        # === 调试日志 ===
        logger.info(f"[用户档案保存] account_id={account_id}, phone_ask_count={profile.phone_ask_count}, wechat_ask_count={profile.wechat_ask_count}, rejected_phone={profile.rejected_phone}")

        if self.use_redis:
            try:
                success = await redis_service.set_json(
                    f"user_profile:{account_id}",
                    profile_dict,
                    ttl=settings.redis_ttl
                )
                if success:
                    # 同时更新内存缓存
                    self._memory_profiles[account_id] = profile
                    return True
                logger.warning(f"Redis save failed, using memory for user_profile: {account_id}")
            except Exception as e:
                logger.error(f"Redis save error: {e}, using memory")

        # 内存模式或Redis失败
        self._memory_profiles[account_id] = profile
        return True

    async def save_user_state(self, user_id: str, state: UserState) -> bool:
        """Save user state to Redis or memory"""
        state_dict = state.to_dict()

        if self.use_redis:
            try:
                success = await redis_service.set_json(
                    f"user_state:{user_id}",
                    state_dict,
                    ttl=settings.redis_ttl
                )
                if success:
                    return True
                logger.warning(f"Redis save failed, using memory for user_state: {user_id}")
            except Exception as e:
                logger.error(f"Redis save error: {e}, using memory")

        # 内存模式或Redis失败
        self._memory_states[user_id] = state
        return True

    async def update_user_profile_field(self, account_id: str, field_name: str, value: Any) -> bool:
        """
        更新用户信息字段

        Args:
            account_id: 用户账号ID
            field_name: 字段名称
            value: 字段值

        Returns:
            bool: 是否更新成功
        """
        profile = await self.get_user_profile(account_id)
        success = profile.update_field(field_name, value)

        if success:
            logger.info(f"Updated {field_name} for user {account_id}: {value}")
            # 保存到Redis
            await self.save_user_profile(account_id, profile)

        return success

    async def delete_user_profile(self, account_id: str) -> bool:
        """
        删除用户档案

        Args:
            account_id: 用户账号ID

        Returns:
            bool: 是否删除成功
        """
        if self.use_redis:
            try:
                await redis_service.delete(f"user_profile:{account_id}")
                logger.info(f"[删除用户档案] Redis: {account_id}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

        # 同时清除内存缓存
        if account_id in self._memory_profiles:
            del self._memory_profiles[account_id]
            logger.info(f"[删除用户档案] 内存: {account_id}")

        return True

    async def get_user_profile_dict(self, account_id: str) -> Dict[str, Any]:
        """
        获取用户信息的字典形式

        Args:
            account_id: 用户账号ID

        Returns:
            Dict[str, Any]: 用户信息字典
        """
        profile = await self.get_user_profile(account_id)
        return profile.to_dict()

    async def get_user_greeting(self, account_id: str) -> str:
        """
        根据用户信息生成合适的称呼

        Args:
            account_id: 用户账号ID

        Returns:
            str: 称呼（如"您"、"小姐姐"、"小哥哥"等）
        """
        profile = await self.get_user_profile(account_id)
        return profile.get_greeting()

    async def get_collection_progress(self, account_id: str) -> float:
        """
        获取用户信息收集进度

        Args:
            account_id: 用户账号ID

        Returns:
            float: 收集进度百分比 (0.0 - 1.0)
        """
        profile = await self.get_user_profile(account_id)
        return profile.get_progress()

    async def get_next_field_to_collect(self, account_id: str) -> Optional[str]:
        """
        获取下一个需要收集的字段

        Args:
            account_id: 用户账号ID

        Returns:
            Optional[str]: 下一个要收集的字段名
        """
        profile = await self.get_user_profile(account_id)
        return profile.get_next_field_to_collect()

    async def get_missing_fields(self, account_id: str) -> list:
        """
        获取未收集的字段列表

        Args:
            account_id: 用户账号ID

        Returns:
            list: 未收集的字段名列表
        """
        profile = await self.get_user_profile(account_id)
        return profile.get_missing_fields()

    async def is_field_error_limit_reached(self, account_id: str, field_name: str, max_errors: int = 2) -> bool:
        """
        检查字段错误次数是否达到限制

        Args:
            account_id: 用户账号ID
            field_name: 字段名
            max_errors: 最大错误次数

        Returns:
            bool: 是否达到错误限制
        """
        profile = await self.get_user_profile(account_id)
        return profile.is_field_error_limit_reached(field_name, max_errors)

    async def reset_field_error_count(self, account_id: str, field_name: str) -> None:
        """
        重置字段错误计数

        Args:
            account_id: 用户账号ID
            field_name: 字段名
        """
        profile = await self.get_user_profile(account_id)
        profile.reset_error_count(field_name)

    async def update_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update user preference"""
        user_state = await self.get_user_state(user_id)
        user_state.update_preference(key, value)
        await self.save_user_state(user_id, user_state)
        self._memory_states[user_id] = user_state
        logger.info(f"Updated preference {key} for user: {user_id}")

    async def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference"""
        user_state = await self.get_user_state(user_id)
        return user_state.get_preference(key, default)

    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user insights"""
        user_state = await self.get_user_state(user_id)
        return user_state.get_user_insights()

    async def get_conversation_context(self, user_id: str, lookback: int = 5) -> Dict[str, Any]:
        """Get conversation context for user"""
        user_state = await self.get_user_state(user_id)
        return user_state.get_conversation_context(lookback)

    async def record_interaction(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record user interaction"""
        user_state = await self.get_user_state(user_id)
        user_state.record_interaction(user_message, assistant_response, metadata)

    async def get_conversation_history(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get conversation history"""
        user_state = await self.get_user_state(user_id)
        history = user_state.conversation_history[offset:offset + limit]

        return {
            "user_id": user_id,
            "conversations": history,
            "total_count": len(user_state.conversation_history),
            "limit": limit,
            "offset": offset
        }

    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get conversation summary"""
        user_state = await self.get_user_state(user_id)
        return user_state.get_conversation_summary()

    async def is_new_user(self, user_id: str, threshold_hours: int = 24) -> bool:
        """Check if user is new"""
        user_state = await self.get_user_state(user_id)
        return user_state.is_new_user(threshold_hours)

    async def is_active_user(self, user_id: str, threshold_hours: int = 168) -> bool:
        """Check if user is active"""
        user_state = await self.get_user_state(user_id)
        return user_state.is_active_user(threshold_hours)

    async def clear_conversation_history(self, user_id: str) -> None:
        """
        清空用户的对话历史

        Args:
            user_id: 用户ID
        """
        user_state = await self.get_user_state(user_id)
        user_state.reset_conversation()
        logger.info(f"Cleared conversation history for user: {user_id}")

    def reset_conversation(self, user_id: str) -> None:
        """Reset user conversation"""
        if user_id in self._memory_states:
            self._memory_states[user_id].reset_conversation()
            logger.info(f"Reset conversation for user: {user_id}")

    def get_all_user_ids(self) -> list:
        """Get all user IDs"""
        return list(self._memory_states.keys())

    def get_all_profile_ids(self) -> list:
        """获取所有用户档案ID"""
        return list(self._memory_profiles.keys())

    def get_active_users_count(self, threshold_hours: int = 168) -> int:
        """Get count of active users"""
        count = 0
        for user_state in self._memory_states.values():
            if user_state.is_active_user(threshold_hours):
                count += 1
        return count

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        total_users = len(self._memory_states)
        active_users = self.get_active_users_count()

        # Calculate total dialogs
        total_dialogs = sum(
            user_state.dialog_count
            for user_state in self._memory_states.values()
        )

        # Get most active users
        active_user_ids = [
            user_id for user_id, user_state in self._memory_states.items()
            if user_state.is_active_user()
        ]

        # Profile statistics
        profile_stats = {
            "total_profiles": len(self._memory_profiles),
            "completed_profiles": sum(
                1 for profile in self._memory_profiles.values()
                if profile.get_progress() >= 0.8
            ),
            "average_progress": 0
        }

        if self._memory_profiles:
            total_progress = sum(profile.get_progress() for profile in self._memory_profiles.values())
            profile_stats["average_progress"] = round(total_progress / len(self._memory_profiles) * 100, 2)

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

        for user_id, user_state in self._memory_states.items():
            if not user_state.is_active_user(threshold_hours):
                user_ids_to_remove.append(user_id)
                removed_count += 1

        for user_id in user_ids_to_remove:
            del self._memory_states[user_id]
            if user_id in self._memory_profiles:
                del self._memory_profiles[user_id]

        if removed_count > 0:
            logger.info(f"Removed {removed_count} inactive users")

        return removed_count

    def export_user_state(self, user_id: str) -> Dict[str, Any]:
        """Export user state for persistence"""
        if user_id in self._memory_states:
            return self._memory_states[user_id].export_state()
        return {}

    def import_user_state(self, user_state_data: Dict[str, Any]) -> None:
        """Import user state from data"""
        from src.models.user_state import UserState
        user_state = UserState.from_dict(user_state_data)
        self._memory_states[user_state.user_id] = user_state

    def cleanup_expired_states(self, max_age_hours: int = 720) -> int:
        """Clean up expired user states"""
        import datetime
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
        expired_users = []

        for user_id, user_state in self._memory_states.items():
            if user_state.last_interaction and user_state.last_interaction < cutoff_time:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self._memory_states[user_id]
            if user_id in self._memory_profiles:
                del self._memory_profiles[user_id]

        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user states")

        return len(expired_users)

    def skip_field(self, account_id: str, field_name: str) -> None:
        """
        跳过某个字段的收集（用户拒绝提供）

        Args:
            account_id: 用户账号ID
            field_name: 字段名
        """
        # 注意：这是一个同步方法，仅用于内存模式
        if account_id in self._memory_profiles:
            self._memory_profiles[account_id].skipped_fields[field_name] = True
            logger.info(f"Field {field_name} marked as skipped for user {account_id}")

    async def skip_user_profile_field(self, account_id: str, field_name: str) -> None:
        """
        跳过某个字段的收集（用户拒绝提供）- 异步版本

        Args:
            account_id: 用户账号ID
            field_name: 字段名
        """
        profile = await self.get_user_profile(account_id)
        profile.skipped_fields[field_name] = True
        await self.save_user_profile(account_id, profile)
        logger.info(f"Field {field_name} marked as skipped for user {account_id}")

    async def add_message_to_history(self, user_id: str, message: Dict[str, Any]) -> None:
        """
        添加消息到历史记录

        Args:
            user_id: 用户ID
            message: 消息字典（格式: {'role': 'user', 'content': 'xxx'}）
        """
        from datetime import datetime

        user_state = await self.get_user_state(user_id)

        # 转换消息格式：{'role': 'user', 'content': 'xxx'} -> {'user_message': 'xxx', 'assistant_response': 'xxx'}
        if message.get('role') == 'user':
            interaction = {
                'user_message': message.get('content', ''),
                'assistant_response': '',  # 将在后续更新
                'timestamp': message.get('timestamp', datetime.now().isoformat())
            }
        elif message.get('role') == 'assistant':
            # 如果是助手消息，需要找到最近的一条用户消息并更新它的 assistant_response
            if user_state.conversation_history:
                last_interaction = user_state.conversation_history[-1]
                last_interaction['assistant_response'] = message.get('content', '')
                last_interaction['timestamp'] = message.get('timestamp', datetime.now().isoformat())
                logger.debug(f"Updated assistant response in history for user: {user_id}")
                return
            else:
                # 没有对应的用户消息，创建一个新的
                interaction = {
                    'user_message': '',
                    'assistant_response': message.get('content', ''),
                    'timestamp': message.get('timestamp', datetime.now().isoformat())
                }
        else:
            # 默认格式
            interaction = message

        if interaction:
            user_state.conversation_history.append(interaction)
            logger.debug(f"Added message to history for user: {user_id}")

    async def save_conversation_context(self, user_id: str, context: Dict[str, Any]) -> None:
        """
        保存对话上下文

        Args:
            user_id: 用户ID
            context: 对话上下文字典
        """
        # 获取当前的 user_state（包含所有字段）
        user_state = await self.get_user_state(user_id)

        # 只更新传入的字段，保留其他字段不变
        if 'recent_responses' in context:
            user_state.recent_responses = context['recent_responses']
        if 'message_count' in context:
            user_state.dialog_count = context['message_count']

        # 持久化到 Redis
        await self.save_user_state(user_id, user_state)

        # 同时更新内存缓存，确保后续 get_user_state 能获取到最新数据
        self._memory_states[user_id] = user_state

        logger.debug(f"Saved conversation context for user: {user_id}")
