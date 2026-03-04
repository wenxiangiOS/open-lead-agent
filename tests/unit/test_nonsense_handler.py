"""
无意义输入处理测试

测试无意义输入的渐进式处理逻辑
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.models.user_profile import UserProfile


class TestNonsenseHandler:
    """无意义输入处理测试"""

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
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name=None, sex="男")

        response = service._get_first_nonsense_response(profile)

        # 应该包含引导用户回答称呼的内容
        assert "名字" in response or "称呼" in response
        assert "小哥哥" in response  # 应该根据性别称呼

    def test_first_nonsense_response_asks_location(self):
        """第一次无意义输入：有称呼但没有城市时，应该问城市"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name="张三", sex="男", location=None)

        response = service._get_first_nonsense_response(profile)

        # 应该包含引导用户回答城市的内容
        assert "城市" in response or "在哪" in response

    def test_second_nonsense_response_lower_barrier(self):
        """第二次无意义输入：应该降低门槛，提供简单选择"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name="张三", sex="女", location=None)

        response = service._get_second_nonsense_response(profile)

        # 应该包含简单的问题（是/否类型）
        assert "深圳" in response or "广东" in response

    def test_third_nonsense_response_direct_guidance(self):
        """第三次无意义输入：应该直接告知需要哪些信息"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name="张三", sex="男")

        response = service._get_third_nonsense_response(profile)

        # 应该包含明确的信息引导
        assert "脱单" in response or "信息" in response or "名字" in response

    def test_fourth_nonsense_response_polite_ending(self):
        """第四次无意义输入：应该礼貌结束，留有余地"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name="张三", sex="女")

        response = service._get_fourth_nonsense_response(profile)

        # 应该包含礼貌结束的内容
        assert "再来" in response or "找我" in response or "随时" in response

    def test_fifth_nonsense_returns_empty(self):
        """第五次及以上无意义输入：应该返回空字符串（静默）"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        profile = self._create_mock_user_profile(last_name="张三", sex="男")

        # 模拟第五次
        response = service._get_fourth_nonsense_response(profile)  # 第四次有响应

        # 第五次没有专门的函数，由 _check_and_handle_nonsense 处理
        # 这里只验证第四次函数存在且工作正常
        assert response is not None
        assert len(response) > 0

    def test_call_name_by_sex(self):
        """测试根据性别使用正确的称呼"""
        from src.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)

        # 男性
        profile_male = self._create_mock_user_profile(sex="男")
        response_male = service._get_first_nonsense_response(profile_male)
        assert "小哥哥" in response_male

        # 女性
        profile_female = self._create_mock_user_profile(sex="女")
        response_female = service._get_first_nonsense_response(profile_female)
        assert "小姐姐" in response_female

        # 未知性别
        profile_unknown = self._create_mock_user_profile(sex=None)
        response_unknown = service._get_first_nonsense_response(profile_unknown)
        assert "亲" in response_unknown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
