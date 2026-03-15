from types import SimpleNamespace
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
async def test_handle_contact_validation_accepts_phone_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_1")
    chat_service.validation_service.validate_contact = AsyncMock(return_value=(True, None, None))
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.contact_service.get_next_action = lambda _profile: SimpleNamespace(value="none")
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: False
    chat_service.collection_policy.decide = lambda _profile, allow_contact_target=False: SimpleNamespace(main_target=None)

    response = await chat_service._handle_contact_validation(
        "user_1",
        profile,
        {"all_fields": [{"field": "phone", "value": "17688654321"}]},
        "原始回复",
    )

    assert response == "好的呀～你的电话我先记下啦。你也可以再简单说说自己的情况～"
    chat_service.validation_service.validate_contact.assert_awaited_once_with(
        "17688654321",
        profile,
        "user_1",
        chat_service.user_service,
    )
    assert profile.phone == "17688654321"
    assert profile.phone_collected is True


@pytest.mark.anyio
async def test_process_chat_request_returns_preset_ending_response_immediately():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_2")
    chat_service.user_service.get_user_profile = AsyncMock(side_effect=[profile, profile, profile])
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.build_main_dialogue_prompt = lambda *args, **kwargs: "prompt"
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={})
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=0)
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="AI原始回复")
    chat_service.extraction_service.extract_json_from_response = lambda _text: {}
    chat_service._process_collection_result = AsyncMock(
        return_value={
            "success": True,
            "response": "预设收尾话术",
            "collected": False,
            "all_fields": [],
        }
    )
    chat_service._handle_contact_validation = AsyncMock(return_value="不该被调用")
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock(return_value=None)

    request = SimpleNamespace(accountId="user_2", question="我已经结婚了", dialogId="dlg_1", sex=None)

    result = await chat_service.process_chat_request(request)

    assert result["response"] == "预设收尾话术"
    chat_service._handle_contact_validation.assert_not_awaited()
