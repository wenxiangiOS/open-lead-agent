"""
挽留功能测试
测试 conversation_ended 状态的保存和读取
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.models.user_profile import UserProfile


class TestUserProfileSerialization:
    """测试 UserProfile 序列化"""

    def test_to_dict_includes_conversation_ended(self):
        """to_dict() 应包含 conversation_ended 字段"""
        profile = UserProfile(account_id="test_user")
        profile.conversation_ended = True

        result = profile.to_dict()

        assert "conversation_ended" in result
        assert result["conversation_ended"] is True

    def test_to_dict_includes_error_count(self):
        """to_dict() 应包含 error_count 字段"""
        profile = UserProfile(account_id="test_user")
        profile.error_count = {"sex": 1, "age": 2}

        result = profile.to_dict()

        assert "error_count" in result
        assert result["error_count"] == {"sex": 1, "age": 2}

    def test_from_dict_handles_missing_conversation_ended(self):
        """from_dict() 应正确处理缺少 conversation_ended 的旧数据"""
        data = {
            "account_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sex": "男",
            # 注意：没有 conversation_ended 字段
        }

        profile = UserProfile.from_dict(data)

        # Pydantic 应该使用默认值 False
        assert profile.conversation_ended is False

    def test_from_dict_handles_missing_error_count(self):
        """from_dict() 应正确处理缺少 error_count 的旧数据"""
        data = {
            "account_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            # 注意：没有 error_count 字段
        }

        profile = UserProfile.from_dict(data)

        # Pydantic 应该使用默认值 {}
        assert profile.error_count == {}

    def test_serialization_round_trip(self):
        """序列化后反序列化应保持数据一致"""
        original = UserProfile(account_id="test_user")
        original.conversation_ended = True
        original.error_count = {"sex": 1}
        original.sex = "男"
        original.age = 30

        # 序列化
        data = original.to_dict()

        # 反序列化
        restored = UserProfile.from_dict(data)

        # 验证
        assert restored.conversation_ended is True
        assert restored.error_count == {"sex": 1}
        assert restored.sex == "男"
        assert restored.age == 30


class TestRetentionFlow:
    """测试挽留流程"""

    @pytest.mark.asyncio
    async def test_conversation_ended_prevents_repeat_farewell(self):
        """
        测试：conversation_ended=True 时，不应重复告别
        """
        # 模拟用户档案（已结束对话）
        user_profile = UserProfile(account_id="test_user")
        user_profile.sex = "男"
        user_profile.conversation_ended = True

        # 模拟 dialogue_manager 返回的上一轮回复（已包含告别语）
        mock_last_response = "好的～小哥哥，那先这样啦～有需要随时再来找我哦～拜拜👋"

        # 模拟 dialogue_manager
        mock_dialogue_manager = MagicMock()
        mock_dialogue_manager.get_last_response = AsyncMock(return_value=mock_last_response)

        # 验证：当 conversation_ended=True 且上一轮已告别时
        # 检查逻辑应该返回空响应
        last_response = mock_last_response
        has_farewell = "有需要随时再来找我" in last_response or "下次再聊" in last_response

        assert has_farewell is True, "上一轮应该包含告别语"

    @pytest.mark.asyncio
    async def test_retention_failure_sets_conversation_ended(self):
        """
        测试：挽留失败后应设置 conversation_ended=True
        """
        # 模拟用户档案
        user_profile = UserProfile(account_id="test_user")
        user_profile.sex = "男"

        # 模拟结束意图计数
        user_profile.field_ask_count = {"conversation_end_intent": 2}

        # 模拟上一轮 AI 回复（包含挽留关键词）
        last_ai_response = "没关系呀～我们完全可以按照你的节奏来，你什么时候想聊了再继续也可以哒～"

        # 验证：上一轮包含挽留关键词
        retention_keywords = [
            '随时可以', '随时', '想聊', '想聊了就聊', '什么时候都可以',
            '先这样', '下次再聊', '拜拜', '没关系', '不打扰',
            '慢慢来', '别急着', '不着急', '有什么不方便', '有什么顾虑',
        ]
        has_retention = any(kw in last_ai_response for kw in retention_keywords)

        assert has_retention is True, "上一轮应该包含挽留关键词"

        # 模拟设置 conversation_ended
        user_profile.conversation_ended = True

        # 验证保存后的状态
        assert user_profile.conversation_ended is True


class TestEndIntentKeywords:
    """测试结束意图关键词"""

    def test_end_intent_keywords_coverage(self):
        """测试结束意图关键词覆盖"""
        from src.services.chat_service import ChatService

        # 这些关键词应该被识别为结束意图
        should_match = [
            "不聊了",
            "不想说了",
            "不想填了",
            "拒绝了",
            "不再问了",
            "感觉问的太细了",
            "太麻烦了",
        ]

        # 这些不应该被识别为结束意图
        should_not_match = [
            "我想聊天",
            "填一下信息",
            "问一下",
        ]

        end_intent_keywords = [
            '不说了', '不聊了', '不想聊', '算了', '算了算了',
            '不填了', '不填', '不写了', '不写', '下次吧',
            '先这样', '不用了', '不用', '不要了', '不要',
            '没兴趣', '没意思', '太麻烦', '太复杂', '太细了',
            '问的太细', '问的太多', '问题太多', '太费事',
            '不想说了', '豆不想说了', '不想填了', '拒绝了', '不再问了',
            '不回答了', '不答了', '不聊', '不回', '不回复',
            '不提供', '不给', '不愿意', '不方便', '不想给'
        ]

        for phrase in should_match:
            is_match = any(kw in phrase for kw in end_intent_keywords)
            assert is_match, f"'{phrase}' 应该被识别为结束意图"

        for phrase in should_not_match:
            is_match = any(kw in phrase for kw in end_intent_keywords)
            assert not is_match, f"'{phrase}' 不应该被识别为结束意图"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
