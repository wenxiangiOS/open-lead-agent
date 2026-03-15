"""
无意义输入处理测试

测试无意义输入的渐进式处理逻辑
"""

from unittest.mock import Mock

import pytest

from src.models.user_profile import UserProfile
from src.services.conversation.input_fallback_service import InputFallbackService


class TestNonsenseHandler:
    """无意义输入处理测试"""

    def _create_service(self):
        return InputFallbackService(
            user_service=Mock(),
            nonsense_prefix="test:nonsense:",
            confirm_prefix="test:confirm:",
        )

    def _create_mock_user_profile(self, **kwargs):
        """创建模拟的用户档案"""
        profile = Mock(spec=UserProfile)
        profile.last_name = kwargs.get('last_name', None)
        profile.sex = kwargs.get('sex', None)
        profile.location = kwargs.get('location', None)
        profile.age = kwargs.get('age', None)
        return profile

    def test_first_nonsense_response_asks_name(self):
        """第一次无意义输入：没有称呼时，应该问称呼"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name=None, sex="男")

        response = service.get_first_nonsense_response(profile)

        assert "小哥哥" in response  # 应该根据性别称呼

    def test_first_nonsense_response_asks_location(self):
        """第一次无意义输入：有称呼但没有城市时，应该问城市"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name="张三", sex="男", location=None)

        response = service.get_first_nonsense_response(profile)

        assert response
        assert "小哥哥" in response

    def test_second_nonsense_response_lower_barrier(self):
        """第二次无意义输入：应该降低门槛，提供简单选择"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name="张三", sex="女", location=None)

        response = service.get_second_nonsense_response(profile)

        assert "城市" in response or "在哪个城市" in response or "先简单点" in response

    def test_third_nonsense_response_direct_guidance(self):
        """第三次无意义输入：应该直接告知需要哪些信息"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name="张三", sex="男")

        response = service.get_third_nonsense_response(profile)

        assert "小哥哥" in response
        assert "聊" in response or "脱单" in response or "打扰" in response

    def test_fourth_nonsense_response_polite_ending(self):
        """第四次无意义输入：应该礼貌结束，留有余地"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name="张三", sex="女")

        response = service.get_closing_response(profile)

        assert "再来" in response or "找我" in response or "随时" in response or "不打扰" in response or "早日脱单" in response

    def test_fifth_nonsense_returns_empty(self):
        """第四次后的关闭回复接口仍然可返回有效内容。"""
        service = self._create_service()
        profile = self._create_mock_user_profile(last_name="张三", sex="男")

        response = service.get_closing_response(profile)

        assert response is not None
        assert len(response) > 0

    def test_call_name_by_sex(self):
        """测试根据性别使用正确的称呼"""
        service = self._create_service()

        # 男性
        profile_male = self._create_mock_user_profile(sex="男")
        response_male = service.get_first_nonsense_response(profile_male)
        assert "小哥哥" in response_male

        # 女性
        profile_female = self._create_mock_user_profile(sex="女")
        response_female = service.get_first_nonsense_response(profile_female)
        assert "小姐姐" in response_female

        # 未知性别
        profile_unknown = self._create_mock_user_profile(sex=None)
        response_unknown = service.get_first_nonsense_response(profile_unknown)
        assert "亲" in response_unknown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
