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
    chat_service._call_ai = AsyncMock(return_value="你再发一个能联系到你的号码就行，不方便的话晚点发也可以。")

    response = await chat_service._handle_contact_validation(
        "user_validation_phone",
        profile,
        {"all_fields": [], "invalid_contact_attempt": "12345"},
        "原始回复",
        "我电话12345",
    )

    assert response == "你再发一个能联系到你的号码就行，不方便的话晚点发也可以。"
    assert chat_service._last_validation_feedback_meta["error_code"] == "CONTACT_INVALID_FORMAT"
    assert chat_service._last_validation_feedback_meta["attempt"] == 1
    chat_service._call_ai.assert_awaited_once()


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
