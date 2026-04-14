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


def test_extract_partner_requirement_hint_merges_profile_raw_and_structured_subslots():
    profile = UserProfile(account_id="test_summary_structured_hint")
    profile.partner_requirement = "同老家在深圳，最好深户，有房有车，不要92"
    profile.partner_pref_location = "深圳"
    profile.partner_pref_education = "学历本科及以上"

    hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(profile=profile)

    assert hint == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"


def test_extract_partner_requirement_hint_reads_structured_subslots_from_collection_result():
    hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(
        collection_result={
            "all_fields": [
                {"field": "partner_pref_location", "value": "深圳"},
                {"field": "partner_pref_education", "value": "学历本科及以上"},
            ]
        }
    )

    assert hint == "深圳，学历本科及以上"


def test_extract_partner_requirement_hint_merges_collection_result_raw_and_structured_subslots():
    hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(
        collection_result={
            "all_fields": [
                {"field": "partner_requirement", "value": "同老家在深圳，最好深户，有房有车，不要92"},
                {"field": "partner_pref_location", "value": "深圳"},
                {"field": "partner_pref_education", "value": "学历本科及以上"},
            ]
        }
    )

    assert hint == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"


def test_extract_partner_requirement_hint_ignores_generic_profile_blob_when_structured_exists():
    profile = UserProfile(account_id="test_summary_structured_hint_generic")
    profile.partner_requirement = "找对象"
    profile.partner_pref_location = "深圳"
    profile.partner_pref_education = "学历本科及以上"

    hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(profile=profile)

    assert hint == "深圳，学历本科及以上"


def test_extract_partner_requirement_hint_hides_pure_gender_only_requirement():
    profile = UserProfile(account_id="test_summary_gender_only_hint")
    profile.partner_requirement = "找男朋友"

    hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(profile=profile)

    assert hint == ""


def test_build_summary_line_prefers_structured_partner_preference_text():
    profile = UserProfile(account_id="test_summary_structured_line")
    profile.location = "深圳"
    profile.partner_requirement = "最好深户，有房有车"
    profile.partner_pref_locality = "同城优先"
    profile.partner_pref_education = "学历本科及以上"

    summary = ChatServiceSummaryHelperService.build_profile_summary_line(profile)

    assert "偏同城" in summary
