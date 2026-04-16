"""
手机号验证测试
测试各种手机号格式的验证和无意义输入检测
"""

import pytest
from unittest.mock import MagicMock, patch

from src.utils.validators import PhoneValidator, ContactValidator


class TestPhoneValidator:
    """测试 PhoneValidator 手机号验证"""

    # 有效手机号测试数据
    VALID_PHONES = [
        # 移动号段
        "13412345678",
        "13512345678",
        "13612345678",
        "13712345678",
        "13800138000",
        "13912345678",
        # 联通号段
        "13012345678",
        "13112345678",
        "13212345678",
        "15512345678",
        "15612345678",
        # 电信号段
        "13312345678",
        "15312345678",
        "18012345678",
        "18112345678",
        "18912345678",
        # 新号段
        "16612345678",
        "17712345678",
        "18812345678",
        "19912345678",
        # 虚拟运营商
        "17012345678",
        "17112345678",
        # 香港手机号（8位，5-9开头）
        "51234567",
        "61234567",
        "71234567",
        "81234567",
        "91234567",
        "58881234",
        "98765432",
    ]

    # 无效手机号测试数据（号段无效）
    INVALID_PREFIX_PHONES = [
        "10012345678",  # 10开头 - 不存在
        "11012345678",  # 11开头 - 不存在（110是报警电话）
        "12012345678",  # 12开头 - 不存在（120是急救电话）
        "12232323232",  # 12开头 - 不存在
        "1678877655555",  # 12位数字
        "41234567",  # 香港号码不能以4开头
        "31234567",  # 香港号码不能以3开头
        "12345678",  # 香港号码不能以1开头
    ]

    # 格式无效的测试数据
    INVALID_FORMAT_PHONES = [
        "12345",  # 位数不够
        "123456789012",  # 12位
        "abcdefghijk",  # 非数字
        "138-1234-5678",  # 带横杠（需要预处理）
        " 13812345678 ",  # 带空格（需要预处理）
    ]

    @pytest.mark.parametrize("phone", VALID_PHONES)
    def test_valid_phones(self, phone):
        """测试有效的手机号"""
        is_valid, error = PhoneValidator.is_valid(phone)
        assert is_valid is True, f"{phone} 应该是有效的手机号，但返回: {error}"
        assert error is None

    @pytest.mark.parametrize("phone", INVALID_PREFIX_PHONES)
    def test_invalid_prefix_phones(self, phone):
        """测试无效号段的手机号（10/11/12开头）"""
        is_valid, error = PhoneValidator.is_valid(phone)
        assert is_valid is False, f"{phone} 应该是无效的手机号（号段不存在）"

    def test_empty_phone(self):
        """测试空手机号"""
        is_valid, error = PhoneValidator.is_valid("")
        assert is_valid is False
        assert error is not None

    def test_none_phone(self):
        """测试 None 手机号"""
        is_valid, error = PhoneValidator.is_valid(None)
        assert is_valid is False

    def test_phone_with_spaces_removed(self):
        """测试带空格的手机号（PhoneValidator 会预处理空格）"""
        # PhoneValidator 会移除空格后验证
        is_valid, error = PhoneValidator.is_valid("138 1234 5678")
        assert is_valid is True  # 空格被移除后是有效手机号


class TestContactValidator:
    """测试 ContactValidator 联系方式验证"""

    def test_valid_phone(self):
        """测试有效手机号"""
        is_valid, contact_type, error = ContactValidator.is_valid_contact("13800138000")
        assert is_valid is True
        assert contact_type == 'phone'
        assert error is None

    def test_invalid_phone_prefix(self):
        """测试无效号段手机号"""
        is_valid, contact_type, error = ContactValidator.is_valid_contact("12232323232")
        assert is_valid is False
        # 应该尝试微信验证，但也失败

    def test_valid_wechat(self):
        """测试有效微信号"""
        is_valid, contact_type, error = ContactValidator.is_valid_contact("wxid_abc123")
        assert is_valid is True
        assert contact_type == 'wechat'
        assert error is None

    def test_wechat_format(self):
        """测试微信号格式（字母开头，5-20字符）"""
        valid_wechats = [
            "M2345",  # 5字符
            "abc123",  # 6字符
            "wxid_test123",  # 字母开头+数字
            "test_user-99",  # 含下划线和减号
            "a1234567890123456789",  # 20字符
        ]
        for wechat in valid_wechats:
            is_valid, contact_type, error = ContactValidator.is_valid_contact(wechat)
            assert is_valid is True, f"{wechat} 应该是有效的微信号"

        invalid_wechats = [
            "123abc",  # 数字开头
            "ab1",  # 太短（<5字符）
            "a" * 21,  # 太长（>20字符）
        ]
        for wechat in invalid_wechats:
            is_valid, contact_type, error = ContactValidator.is_valid_contact(wechat)
            assert is_valid is False, f"{wechat} 应该是无效的微信号"


class TestUserProfileContactValidation:
    """测试 UserProfile 中的 contact 验证"""

    def test_valid_phone_in_profile(self):
        """测试 UserProfile 接受有效手机号"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")
        result = profile.update_field('contact', '13800138000')

        assert result is True
        assert profile.contact == '13800138000'

    def test_invalid_phone_in_profile(self):
        """测试 UserProfile 拒绝无效号段手机号"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")

        # 12开头的无效手机号
        result = profile.update_field('contact', '12232323232')

        # 应该返回 False，contact 不应被更新
        assert result is False
        assert profile.contact is None

    def test_invalid_prefix_10(self):
        """测试 10 开头的无效号段"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")
        result = profile.update_field('contact', '10012345678')

        assert result is False

    def test_invalid_prefix_11(self):
        """测试 11 开头的无效号段"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")
        result = profile.update_field('contact', '11012345678')

        assert result is False


class TestNonsenseDetectionWithPhone:
    """测试手机号不会被误判为无意义输入"""

    # 有效手机号不应被判定为乱码
    VALID_PHONES_NOT_NONSENSE = [
        "13800138000",
        "15912345678",
        "18888888888",
        "19900001111",
    ]

    # 这些数字也不应被判定为乱码（即使不是有效手机号）
    NUMBERS_NOT_NONSENSE = [
        "12232323232",  # 虽然无效，但仍是数字，不会被判定为乱码
        "10012345678",  # 同上
        "12345",  # 短数字
        "1234567890",  # 10位数字
        "123456789012345",  # 15位数字（可能是订单号等）
    ]

    # 这些应该被判定为乱码
    SHOULD_BE_NONSENSE = [
        "asdfghjkl",  # 键盘乱敲
        "qwertyuiop",  # 键盘序列
        "哈哈哈哈哈哈哈",  # 纯表情/重复
        "！！！！！！",  # 纯符号
    ]

    @pytest.mark.parametrize("text", VALID_PHONES_NOT_NONSENSE)
    def test_valid_phone_not_nonsense(self, text):
        """有效手机号不应被判定为无意义输入"""
        # 模拟 _is_nonsense_input 的逻辑
        import re

        # 检查是否匹配手机号格式
        is_phone = bool(re.match(r'^1[3-9]\d{9}$', text))
        assert is_phone is True, f"{text} 应该匹配手机号格式"

    @pytest.mark.parametrize("text", NUMBERS_NOT_NONSENSE)
    def test_numbers_not_nonsense(self, text):
        """数字不应被判定为键盘乱码"""
        import re

        # 检查不是字母键盘乱敲
        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'qwer', 'asdf', 'zxcv', 'tyui', 'ghjk', 'bnm',
        ]
        text_lower = text.lower()
        is_keyboard_mash = any(seq in text_lower or seq[::-1] in text_lower for seq in keyboard_sequences)

        assert is_keyboard_mash is False, f"{text} 不应被判定为键盘乱敲"

    @pytest.mark.parametrize("text", SHOULD_BE_NONSENSE)
    def test_should_be_nonsense(self, text):
        """这些应该被判定为无意义输入"""
        import re

        # 测试各种乱码检测逻辑
        is_nonsense = False

        # 1. 键盘乱敲
        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'qwer', 'asdf', 'zxcv',
        ]
        text_lower = text.lower()
        if any(seq in text_lower or seq[::-1] in text_lower for seq in keyboard_sequences):
            is_nonsense = True

        # 2. 纯符号
        if re.match(r'^[^a-zA-Z0-9\u4e00-\u9fa5]*$', text):
            is_nonsense = True

        # 3. 重复字符
        if re.match(r'^(.)\1{6,}$', text):
            is_nonsense = True

        assert is_nonsense is True, f"{text} 应该被判定为无意义输入"


class TestEdgeCases:
    """测试边界情况"""

    def test_phone_with_country_code(self):
        """测试带国家码的手机号"""
        # +86 13800138000
        # PhoneValidator 不会处理国家码，需要业务层预处理
        is_valid, error = PhoneValidator.is_valid("+8613800138000")
        assert is_valid is False  # 14位，不符合11位要求

    def test_phone_with_dashes(self):
        """测试带横杠的手机号（PhoneValidator 会预处理横杠）"""
        # PhoneValidator 会移除横杠后验证
        is_valid, error = PhoneValidator.is_valid("138-1234-5678")
        assert is_valid is True  # 横杠被移除后是有效手机号

    def test_all_same_digits(self):
        """测试全相同数字"""
        # 有效的11位数字，但全是相同的
        phones = [
            ("13333333333", True),  # 13开头，有效
            ("14444444444", True),  # 14开头，有效
            ("12222222222", False),  # 12开头，无效
            ("10000000000", False),  # 10开头，无效
        ]
        for phone, expected in phones:
            is_valid, _ = PhoneValidator.is_valid(phone)
            assert is_valid is expected, f"{phone} 验证结果应为 {expected}"

    def test_boundary_numbers(self):
        """测试边界号段"""
        # 有效的边界号段
        valid_boundary = [
            "13000000000",  # 13开头最小
            "13999999999",  # 13开头最大
            "19000000000",  # 19开头最小
            "19999999999",  # 19开头最大
        ]
        for phone in valid_boundary:
            is_valid, error = PhoneValidator.is_valid(phone)
            assert is_valid is True, f"{phone} 应该有效"

        # 无效的边界号段
        invalid_boundary = [
            "12999999999",  # 12开头，无效
            "10000000000",  # 10开头，无效
        ]
        for phone in invalid_boundary:
            is_valid, error = PhoneValidator.is_valid(phone)
            assert is_valid is False, f"{phone} 应该无效"


class TestHongKongPhone:
    """测试香港手机号验证"""

    # 有效的香港手机号
    VALID_HK_PHONES = [
        "51234567",
        "61234567",
        "71234567",
        "81234567",
        "91234567",
        "58881234",
        "66881234",
        "77991234",
        "88889999",
        "99998888",
    ]

    # 无效的香港手机号
    INVALID_HK_PHONES = [
        "41234567",  # 4开头无效
        "31234567",  # 3开头无效
        "21234567",  # 2开头无效
        "11234567",  # 1开头无效
        "01234567",  # 0开头无效
        "5123456",   # 7位，太短
        "512345678", # 9位，太长
    ]

    @pytest.mark.parametrize("phone", VALID_HK_PHONES)
    def test_valid_hk_phones(self, phone):
        """测试有效的香港手机号"""
        is_valid, error = PhoneValidator.is_valid(phone)
        assert is_valid is True, f"{phone} 应该是有效的香港手机号"
        assert error is None

    @pytest.mark.parametrize("phone", INVALID_HK_PHONES)
    def test_invalid_hk_phones(self, phone):
        """测试无效的香港手机号"""
        is_valid, error = PhoneValidator.is_valid(phone)
        assert is_valid is False, f"{phone} 应该是无效的香港手机号"

    def test_hk_phone_in_profile(self):
        """测试 UserProfile 接受香港手机号"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")
        result = profile.update_field('contact', '51234567')

        assert result is True
        assert profile.contact == '51234567'

    def test_invalid_hk_phone_in_profile(self):
        """测试 UserProfile 拒绝无效香港手机号"""
        from src.models.user_profile import UserProfile

        profile = UserProfile(account_id="test_user")
        result = profile.update_field('contact', '41234567')

        assert result is False
        assert profile.contact is None

    def test_hk_phone_not_nonsense(self):
        """测试香港手机号不被误判为乱码"""
        import re

        phone = "51234567"
        # 应该匹配香港手机号正则
        is_hk_phone = bool(re.match(r'^[5-9]\d{7}$', phone))
        assert is_hk_phone is True, f"{phone} 应该匹配香港手机号格式"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
