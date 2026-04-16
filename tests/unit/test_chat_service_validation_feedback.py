from unittest.mock import AsyncMock

import pytest

from src.models.user_profile import UserProfile
from src.services.core.chat_service import ChatService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    user_service = AsyncMock()
    return ChatService(_FakeAIService(), user_service)


@pytest.mark.anyio
async def test_handle_contact_validation_returns_ai_feedback_and_meta_for_invalid_phone():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone")
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(
            False,
            {
                "code": "CONTACT_INVALID_FORMAT",
                "field": "contact",
                "detail": "号码长度不合法",
                "attempt": 1,
                "silent": False,
            },
            None,
        )
    )
    response = await chat_service._handle_contact_validation(
        "user_validation_phone",
        profile,
        {"all_fields": [], "invalid_contact_attempt": "12345"},
        "原始回复",
        "我电话12345",
    )

    assert "手机号" in response or "号码" in response
    assert "顾虑" not in response
    assert "晚点发也可以" not in response
    assert chat_service._last_validation_feedback_meta["error_code"] == "CONTACT_INVALID_FORMAT"
    assert chat_service._last_validation_feedback_meta["attempt"] == 1


@pytest.mark.anyio
async def test_handle_contact_validation_keeps_silent_on_third_invalid_attempt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_silent")
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(
            False,
            {
                "code": "CONTACT_INVALID_FORMAT",
                "field": "contact",
                "detail": "号码长度不合法",
                "attempt": 3,
                "silent": True,
            },
            None,
        )
    )
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    response = await chat_service._handle_contact_validation(
        "user_validation_silent",
        profile,
        {"all_fields": [], "invalid_contact_attempt": "12345"},
        "原始回复",
        "我电话12345",
    )

    assert response == ""
    assert chat_service._last_validation_feedback_meta["error_code"] == "CONTACT_INVALID_FORMAT"
    assert chat_service._last_validation_feedback_meta["silent"] is True
    chat_service._call_ai.assert_not_awaited()


@pytest.mark.anyio
async def test_handle_contact_validation_short_phone_uses_format_correction_copy_without_privacy_hallucination():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_short_phone")
    profile.last_contact_request_type = "phone"
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(
            False,
            {
                "code": "CONTACT_INVALID_FORMAT",
                "field": "contact",
                "detail": "号码长度不合法",
                "attempt": 1,
                "silent": False,
            },
            None,
        )
    )

    response = await chat_service._handle_contact_validation(
        "user_validation_short_phone",
        profile,
        {"all_fields": [], "invalid_contact_attempt": "1723723478"},
        "原始回复",
        "1723723478",
    )

    assert "差一位" in response or "核对" in response
    assert "顾虑" not in response
    assert "隐私" not in response


@pytest.mark.anyio
async def test_handle_contact_validation_retries_invalid_phone_even_when_next_action_is_none():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone_none")
    profile.last_contact_request_type = "phone"
    profile.phone_ask_count = 2
    chat_service.contact_service.get_next_action = lambda _profile, _message="": type("A", (), {"value": "none"})()
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(
            False,
            {
                "code": "CONTACT_INVALID_FORMAT",
                "field": "contact",
                "detail": "号码长度不合法",
                "attempt": 1,
                "silent": False,
            },
            None,
        )
    )
    chat_service._call_ai = AsyncMock(return_value="这个号码看起来不太对，你直接发常用手机号就行。")

    response = await chat_service._handle_contact_validation(
        "user_validation_phone_none",
        profile,
        {"all_fields": []},
        "原始回复",
        "1768876543",
    )

    assert "号码" in response or "手机号" in response
    assert "存好" not in response
    chat_service.validation_service.validate_contact.assert_awaited_once()


@pytest.mark.anyio
async def test_handle_contact_validation_prefers_invalid_retry_over_ai_extracted_invalid_contact():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone_extracted_invalid")
    profile.last_contact_request_type = "phone"
    profile.phone_ask_count = 2
    chat_service.contact_service.get_next_action = lambda _profile, _message="": type("A", (), {"value": "none"})()
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(
            False,
            {
                "code": "CONTACT_INVALID_FORMAT",
                "field": "contact",
                "detail": "号码长度不合法",
                "attempt": 1,
                "silent": False,
            },
            None,
        )
    )
    chat_service._call_ai = AsyncMock(return_value="这个号码看起来不太对，你直接发常用手机号就行。")

    response = await chat_service._handle_contact_validation(
        "user_validation_phone_extracted_invalid",
        profile,
        {
            "all_fields": [{"field": "contact", "value": "1768876543"}],
            "invalid_contact_attempt": "1768876543",
        },
        "好哒我记下来啦，后面联系你会方便些。",
        "1768876543",
    )

    assert "号码" in response or "手机号" in response
    assert "记下" not in response
    chat_service.validation_service.validate_contact.assert_awaited_once()


@pytest.mark.anyio
async def test_handle_contact_validation_does_not_force_same_turn_wechat_followup_after_valid_phone_when_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone_success")
    profile.location = "深圳"
    profile.sex = "女"
    profile.age = 28
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.phone_ask_count = 1
    profile.last_contact_request_type = "phone"
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(True, None, None)
    )

    response = await chat_service._handle_contact_validation(
        "user_validation_phone_success",
        profile,
        {"all_fields": [{"field": "contact", "value": "17688987678"}]},
        "电话我记下啦。",
        "17688987678",
    )

    assert response == "电话我记下啦。"
    assert profile.phone == "17688987678"
    assert profile.phone_collected is True


@pytest.mark.anyio
async def test_handle_contact_validation_does_not_force_same_turn_phone_followup_after_valid_wechat_when_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_wechat_success")
    profile.location = "深圳"
    profile.sex = "女"
    profile.age = 28
    profile.education = "本科"
    profile.occupation = "IT"
    profile.wechat_ask_count = 1
    profile.last_contact_request_type = "wechat"

    response = await chat_service._handle_contact_validation(
        "user_validation_wechat_success",
        profile,
        {"all_fields": [{"field": "wechat", "value": "wx889900"}]},
        "微信我记下啦。",
        "wx889900",
    )

    assert "电话" not in response
    assert profile.wechat == "wx889900"
    assert profile.wechat_collected is True


@pytest.mark.anyio
async def test_handle_contact_validation_accepts_short_wechat_in_phone_context():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_short_wechat_switch")
    profile.location = "深圳"
    profile.sex = "女"
    profile.age = 32
    profile.education = "港硕"
    profile.occupation = "外贸"
    profile.phone_ask_count = 1
    profile.last_contact_request_type = "phone"

    response = await chat_service._handle_contact_validation(
        "user_validation_short_wechat_switch",
        profile,
        {"all_fields": []},
        "原始回复",
        "可以微信M2345联系 白天上班也不方便接电话",
    )

    assert "手机号" not in response
    assert "号码" not in response
    assert profile.wechat == "M2345"
    assert profile.wechat_collected is True
    assert profile.phone_collected is False


@pytest.mark.anyio
async def test_handle_contact_validation_adds_wechat_followup_after_valid_phone_when_profile_complete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone_complete")
    profile.location = "深圳"
    profile.sex = "女"
    profile.age = 28
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.marital_status = "未婚单身"
    profile.monthly_income = "18万左右"
    profile.partner_requirement = "90后，180cm及以上，工作稳定"
    profile.partner_gender_preference = "男生"
    profile.phone_ask_count = 1
    profile.last_contact_request_type = "phone"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "partner_gender_preference": True,
        }
    )
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(True, None, None)
    )

    response = await chat_service._handle_contact_validation(
        "user_validation_phone_complete",
        profile,
        {"all_fields": [{"field": "contact", "value": "17688987678"}]},
        "我这边已经把你的基本情况和择偶要求都记下来啦。",
        "17688987678",
    )

    assert "微信" in response
    assert profile.phone == "17688987678"
    assert profile.phone_collected is True


@pytest.mark.anyio
async def test_handle_contact_validation_adds_wechat_followup_after_valid_phone_when_values_exist_without_progress_flags():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_validation_phone_complete_value_fallback")
    profile.location = "深圳"
    profile.sex = "女"
    profile.age = 28
    profile.age_label = "98年"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.marital_status = "未婚单身"
    profile.monthly_income = "18万左右"
    profile.partner_requirement = "180cm及以上，90后，工作稳定"
    profile.partner_gender_preference = "男生"
    profile.phone_ask_count = 2
    profile.last_contact_request_type = "phone"
    profile.phone_invalid_input_retry_count = 1
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(True, None, None)
    )

    response = await chat_service._handle_contact_validation(
        "user_validation_phone_complete_value_fallback",
        profile,
        {"all_fields": [{"field": "contact", "value": "17688654678"}]},
        "之前了解到你想找90后工作稳定的男生，我记下来啦。你要是还有其他比较在意的择偶小细节也可以和我说说，我后面帮你留意的时候也能多参考着点~",
        "17688654678",
    )

    assert "微信" in response
    assert "择偶小细节" not in response
    assert profile.phone == "17688654678"
    assert profile.phone_collected is True


def test_error_response_preserves_error_code_and_details():
    chat_service = _build_chat_service()

    payload = chat_service._error_response(
        "服务暂时不可用，请稍后重试",
        "dlg_1",
        error_code="INTERNAL_ERROR",
        details={"type": "RuntimeError"},
    )

    assert payload["success"] is False
    assert payload["error_code"] == "INTERNAL_ERROR"
    assert payload["details"] == {"type": "RuntimeError"}
