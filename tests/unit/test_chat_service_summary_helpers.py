from src.models.user_profile import UserProfile
from src.services.core.chat_service import ChatService
from src.services.core.chat_service_summary_helper_service import ChatServiceSummaryHelperService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), object())


def test_should_not_emit_summary_with_few_fields():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="test_summary_few")
    profile.collection_progress["sex"] = True
    profile.collection_progress["age"] = True

    should_emit = chat_service._should_emit_profile_summary(profile, current_message_count=5)
    assert should_emit is False


def test_should_emit_summary_with_enough_fields_still_defaults_to_false():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="test_summary_enough")
    profile.collection_progress["sex"] = True
    profile.collection_progress["age"] = True
    profile.age = "28"
    profile.collection_progress["location"] = True
    profile.location = "深圳"
    profile.collection_progress["education"] = True
    profile.education = "本科"
    profile.collection_progress["monthly_income"] = True
    profile.monthly_income = "3万"

    should_emit = chat_service._should_emit_profile_summary(profile, current_message_count=10)
    assert should_emit is False


def test_should_not_emit_summary_too_frequently():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="test_summary_freq")
    profile.collection_progress["sex"] = True
    profile.collection_progress["age"] = True
    profile.age = "28"
    profile.collection_progress["location"] = True
    profile.location = "深圳"
    profile.collection_progress["education"] = True
    profile.education = "本科"
    profile.collection_progress["partner_requirement"] = True
    profile.partner_requirement = "同城"
    profile.last_profile_summary_turn = 8

    should_emit = chat_service._should_emit_profile_summary(profile, current_message_count=10)
    assert should_emit is False


def test_build_summary_line_includes_key_fields():
    profile = UserProfile(account_id="test_summary_build")
    profile.location = "深圳"
    profile.age = "28"
    profile.partner_requirement = "同城"

    summary = ChatServiceSummaryHelperService.build_profile_summary_line(profile)
    assert summary
    assert "深圳" in summary
    assert "28" in summary or "岁" in summary
    assert "同城" in summary or "偏同城" in summary


def test_build_summary_line_returns_empty_for_empty_profile():
    profile = UserProfile(account_id="test_summary_empty")

    summary = ChatServiceSummaryHelperService.build_profile_summary_line(profile)
    assert summary == ""


def test_summary_format_is_natural():
    profile = UserProfile(account_id="test_summary_format")
    profile.location = "深圳"
    profile.age = "90后"
    profile.partner_requirement = "同城，90后"

    summary = ChatServiceSummaryHelperService.build_profile_summary_line(profile)
    assert summary.startswith("你")
    assert summary.endswith("。")
    assert "是吧" not in summary
