"""
数据验证服务

负责验证用户提交的数据，特别是联系方式
"""

import logging
from typing import Dict, Any, Optional, Tuple
from src.models.user_profile import UserProfile
from src.utils.validators import (
    PhoneValidator,
    WechatValidator,
    ContactValidator,
    AgeValidator,
    HeightValidator
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    数据验证服务

    职责：
    1. 验证手机号格式
    2. 验证微信号格式
    3. 验证其他联系方式
    4. 生成验证失败的提示消息
    """

    def __init__(self):
        """初始化验证服务"""
        pass

    async def validate_contact(
        self,
        contact: str,
        user_profile: UserProfile,
        account_id: str,
        user_service = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        验证联系方式

        Args:
            contact: 联系方式（手机号或微信）
            user_profile: 用户档案
            account_id: 用户 ID
            user_service: 用户服务（可选，用于保持状态一致性）

        Returns:
            Tuple[bool, Optional[str], Optional[str]]:
                (是否有效, 错误消息, 成功消息)
        """
        # 如果没有传入user_service，创建新的实例
        if user_service is None:
            from src.services.data.user_service import UserService
            user_service = UserService()

        user_state = await user_service.get_user_state(account_id)

        # 检查是否是手机号或微信标识
        if contact in ['phone', 'wechat']:
            return (False, None, None)

        # 使用统一验证器
        is_valid, contact_type, error_msg = ContactValidator.is_valid_contact(contact)

        if not is_valid:
            # 增加错误次数并保存
            error_count = user_state.increment_contact_error()
            await user_service.save_user_state(account_id, user_state)

            # 根据用户性别选择称呼
            call_name = user_profile.get_greeting() if user_profile else "亲"

            # 根据错误次数给出不同提示
            if error_count == 1:
                # 第1次错误：提示手机号格式问题（添加称呼前缀）
                return (False, f"{call_name}，{error_msg}", None)
            elif error_count == 2:
                # 第2次错误：提示微信也可以
                return (False, f"嗯嗯，{call_name}不方便留手机号的话，微信号也可以呀～方便留个微信号吗呀", None)
            else:
                # 第3次及以上：委婉结束话题
                user_profile.skipped_fields['contact'] = True
                await user_service.save_user_profile(account_id, user_profile)
                return (False, "", None)  # 返回空消息，不回复

        # 验证通过，重置错误计数
        user_state.reset_contact_error_count()
        await user_service.save_user_state(account_id, user_state)

        # 确保联系方式的收集进度被标记为 True
        user_profile.collection_progress['contact'] = True
        await user_service.save_user_profile(account_id, user_profile)
        logger.info(f"[联系方式验证成功] 已标记 collection_progress['contact'] = True")

        # 不再返回收尾话术，而是返回 None，让后续逻辑询问择偶要求
        # 收尾话术会在择偶要求收集后才触发
        return (True, None, None)

    def validate_phone(self, phone: str) -> Tuple[bool, Optional[str]]:
        """
        验证手机号格式

        Args:
            phone: 手机号

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        return PhoneValidator.is_valid(phone)

    def validate_wechat(self, wechat: str) -> Tuple[bool, Optional[str]]:
        """
        验证微信号格式

        Args:
            wechat: 微信号

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        return WechatValidator.is_valid(wechat)

    def validate_age(self, age) -> Tuple[bool, Optional[str]]:
        """
        验证年龄

        Args:
            age: 年龄

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        return AgeValidator.is_valid(age)

    def validate_height(self, height) -> Tuple[bool, Optional[str]]:
        """
        验证身高

        Args:
            height: 身高

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        return HeightValidator.is_valid(height)

    def should_skip_field(
        self,
        field: str,
        error_count: int,
        max_errors: int = 2
    ) -> bool:
        """
        判断是否应该跳过某个字段（多次验证失败后）

        Args:
            field: 字段名
            error_count: 错误次数
            max_errors: 最大错误次数

        Returns:
            bool: 是否应该跳过
        """
        if error_count >= max_errors:
            logger.info(f"[跳过字段] {field} 错误次数过多 ({error_count}次)，跳过")
            return True
        return False
