from src.models.user_profile import UserProfile
from src.services.core.chat_service import ChatService
from src.services.core.chat_service_bridge_text_service import ChatServiceBridgeTextService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), object())


def test_bridge_prefix_generated_for_faq_type():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix("faq")

    assert prefix
    assert prefix.endswith("。") or prefix.endswith(" ")
    assert any(keyword in prefix for keyword in ["先", "这块", "这个", "放一边"])


def test_bridge_prefix_generated_for_boundary_type():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix("boundary")

    assert prefix
    assert any(keyword in prefix for keyword in ["先", "这个", "放一边", "回到"])


def test_bridge_prefix_generated_for_complaint_type():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix("complaint")

    assert prefix
    assert any(keyword in prefix for keyword in ["节奏", "先", "换个"])


def test_bridge_prefix_empty_for_none():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix(None)
    assert prefix == ""


def test_bridge_prefix_empty_for_empty_string():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix("")
    assert prefix == ""


def test_bridge_prefix_fallback_for_unknown_type():
    prefix = ChatServiceBridgeTextService.build_bridge_back_prefix("unknown_type")
    assert prefix


def test_user_profile_has_bridge_back_fields():
    profile = UserProfile(account_id="test_bridge_fields")
    assert hasattr(profile, "needs_bridge_back")
    assert hasattr(profile, "last_side_topic_type")
    assert hasattr(profile, "complaint_cooldown_until")
    assert hasattr(profile, "last_profile_summary_turn")
    assert profile.needs_bridge_back is False
    assert profile.last_side_topic_type is None


def test_bridge_back_markers_are_set_after_faq():
    profile = UserProfile(account_id="test_faq_bridge")
    profile.needs_bridge_back = True
    profile.last_side_topic_type = "faq"
    assert profile.needs_bridge_back is True
    assert profile.last_side_topic_type == "faq"


def test_bridge_back_markers_are_reset_after_use():
    profile = UserProfile(account_id="test_bridge_reset")
    profile.needs_bridge_back = True
    profile.last_side_topic_type = "faq"
    profile.needs_bridge_back = False
    profile.last_side_topic_type = None
    assert profile.needs_bridge_back is False
    assert profile.last_side_topic_type is None
