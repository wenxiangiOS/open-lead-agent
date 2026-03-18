"""
统一验证工具

所有数据验证逻辑的集中管理，避免重复代码
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class PhoneValidator:
    """手机号验证器"""

    # 中国大陆手机号：1开头，第二位3-9，共11位
    # 香港手机号：5/6/7/8/9开头，共8位
    PATTERN_MAINLAND = r'^1[3-9]\d{9}$'
    PATTERN_HONGKONG = r'^[5-9]\d{7}$'

    @classmethod
    def is_valid(cls, phone: str) -> Tuple[bool, Optional[str]]:
        """
        验证手机号格式（支持中国大陆和香港）

        Args:
            phone: 手机号

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        if not phone:
            return False, "方便留个能联系到的手机号或微信号吗呀～"

        # 统一提取数字，兼容空格/横杠/+86/86 前缀
        clean_phone = re.sub(r'\D', '', phone)
        if clean_phone.startswith('86') and len(clean_phone) == 13 and clean_phone[2] == '1':
            clean_phone = clean_phone[2:]

        # 检查中国大陆手机号（11位）或香港手机号（8位）
        if re.match(cls.PATTERN_MAINLAND, clean_phone):
            return True, None
        if re.match(cls.PATTERN_HONGKONG, clean_phone):
            return True, None

        return False, "这个号码好像位数不对呢～能确认下是手机号或微信号吗呀"


class WechatValidator:
    """微信号验证器"""

    # 微信号规则：6-20位，字母开头，可包含字母、数字、下划线、减号
    PATTERN = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'

    @classmethod
    def is_valid(cls, wechat: str) -> Tuple[bool, Optional[str]]:
        """
        验证微信号格式

        Args:
            wechat: 微信号

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        if not wechat:
            return False, "方便留个能联系到的微信号吗呀～"

        if not re.match(cls.PATTERN, wechat):
            return False, "这个微信号好像格式不太对呢～是字母开头的6-20位字符吗呀"

        return True, None


class ContactValidator:
    """联系方式验证器（统一入口）"""

    @classmethod
    def is_valid_contact(cls, contact: str) -> Tuple[bool, str, Optional[str]]:
        """
        验证联系方式（手机号或微信）

        Args:
            contact: 联系方式

        Returns:
            Tuple[bool, str, Optional[str]]: (是否有效, 类型, 错误消息)
        """
        if not contact or contact in ['phone', 'wechat']:
            return False, 'unknown', "方便留个能联系到的手机号或微信号吗呀～"

        # 尝试验证为手机号
        is_valid_phone, phone_error = PhoneValidator.is_valid(contact)
        if is_valid_phone:
            return True, 'phone', None

        # 尝试验证为微信号
        is_valid_wechat, wechat_error = WechatValidator.is_valid(contact)
        if is_valid_wechat:
            return True, 'wechat', None

        # 都不是，返回错误
        return False, 'unknown', phone_error or wechat_error or "方便留个能联系到的手机号或微信号吗呀～"


class AgeValidator:
    """年龄验证器"""

    @classmethod
    def is_valid(cls, age) -> Tuple[bool, Optional[str]]:
        """
        验证年龄

        Args:
            age: 年龄

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        try:
            age_int = int(age)
            if 18 <= age_int <= 100:
                return True, None
            return False, "年龄需要在18-100岁之间"
        except (ValueError, TypeError):
            return False, "年龄格式不正确"


class HeightValidator:
    """身高验证器"""

    @classmethod
    def is_valid(cls, height) -> Tuple[bool, Optional[str]]:
        """
        验证身高

        Args:
            height: 身高

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        try:
            # 移除 "cm" 单位
            if isinstance(height, str):
                height = height.replace('cm', '').replace('厘米', '').strip()

            height_int = int(height)
            if 140 <= height_int <= 220:
                return True, None
            return False, "身高需要在140-220cm之间"
        except (ValueError, TypeError):
            return False, "身高格式不正确"


class InputValidator:
    """输入验证器"""

    # 无效输入模式
    INVALID_PATTERNS = [
        r'^[^a-zA-Z0-9\u4e00-\u9fa5]*$',  # 纯符号
        r'^(.)\1{20,}$',                   # 重复字符超过20次
        r'[\x00-\x08\x0b-\x0c\x0e-\x1f]',  # 控制字符
    ]

    # 最小有效长度
    MIN_LENGTH = 1

    # 最大有效长度
    MAX_LENGTH = 500

    @classmethod
    def is_understandable(cls, text: str) -> bool:
        """
        检查输入是否可理解

        Args:
            text: 输入文本

        Returns:
            bool: 是否可理解
        """
        if not text:
            return False

        # 检查长度
        if len(text) < cls.MIN_LENGTH or len(text) > cls.MAX_LENGTH:
            return False

        # 检查无效模式
        for pattern in cls.INVALID_PATTERNS:
            if re.match(pattern, text):
                return False

        # 检查是否包含有效内容
        # 至少包含一个有效字符（中文、英文、数字）
        has_valid_char = bool(re.search(
            r'[a-zA-Z0-9\u4e00-\u9fa5]',
            text
        ))

        return has_valid_char


class RefusalDetector:
    """拒绝检测器"""

    # 拒绝关键词
    REFUSAL_KEYWORDS = [
        '不想说', '不想提供', '不想给', '不能说', '不能提供', '不能给',
        '不想告诉你', '不想告诉', '不方便', '不方便说', '不方便提供',
        '不愿意', '不愿意说', '不愿意提供', '拒绝', '不想说这个',
        '保密', '隐私', '不方便透露', '保密起见', '隐私问题',
        '不想留', '不能留', '不方便留', '先不', '以后再说', '下次再说',
        '还没准备好', '暂时不说', '暂时不想', '暂时不提供',
        '不能告诉你', '无法提供', '无法告知'
    ]

    @classmethod
    def is_refusing(cls, text: str) -> bool:
        """
        检测用户是否拒绝

        Args:
            text: 用户输入

        Returns:
            bool: 是否拒绝
        """
        if not text:
            return False

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cls.REFUSAL_KEYWORDS)
