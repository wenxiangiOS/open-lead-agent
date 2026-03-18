from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.config.settings import settings
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
        "我电话17688654321",
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
async def test_handle_contact_validation_retries_invalid_phone_attempt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_3")
    chat_service.validation_service.validate_contact = AsyncMock(
        return_value=(False, "小姐姐，这个号码好像位数不对呢～能确认下是手机号或微信号吗呀", None)
    )

    response = await chat_service._handle_contact_validation(
        "user_3",
        profile,
        {"all_fields": [], "invalid_contact_attempt": "12345"},
        "原始回复",
        "我电话12345",
    )

    assert "确认" in response or "号码" in response or "电话" in response
    chat_service.validation_service.validate_contact.assert_awaited_once_with(
        "12345",
        profile,
        "user_3",
        chat_service.user_service,
    )


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
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
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


@pytest.mark.anyio
async def test_handle_contact_validation_does_not_reask_phone_after_wechat_if_phone_exists():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_4")
    profile.phone = "17688654321"
    profile.phone_collected = True
    profile.wechat = "wx123456"
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: True
    chat_service.contact_service.get_next_action = lambda _profile: SimpleNamespace(value="none")
    chat_service._mark_remaining_fields_as_skipped = AsyncMock(return_value=None)

    response = await chat_service._handle_contact_validation(
        "user_4",
        profile,
        {"all_fields": [{"field": "wechat", "value": "wx123456"}]},
        "原始回复",
        "我微信wx123456",
    )

    assert "电话方便" not in response


@pytest.mark.anyio
async def test_process_chat_request_does_not_reset_empty_profile_mid_session():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_5")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=2)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.input_fallback_service.check_and_handle_nonsense = AsyncMock(return_value="兜底回复")

    request = SimpleNamespace(accountId="user_5", question="你好", dialogId="dlg_2", sex=None)

    result = await chat_service.process_chat_request(request)

    assert result["response"] == "兜底回复"
    chat_service.input_fallback_service.reset_nonsense_count.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_first_turn_greeting_still_uses_humanized_fast_path_with_prefilled_sex():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_6")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=0)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=1)
    chat_service.input_fallback_service.check_and_handle_nonsense = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    request = SimpleNamespace(accountId="user_6", question="你好", dialogId="dlg_3", sex="女")
    result = await chat_service.process_chat_request(request)

    assert result["success"] is True
    assert result["response"]
    assert any(token in result["response"] for token in ["先", "聊", "问你", "在呢", "在的"])
    chat_service._call_ai.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_followup_greeting_uses_lightweight_path_when_ai_prob_zero(monkeypatch):
    monkeypatch.setenv("MQ_FOLLOWUP_GREETING_AI_PROB", "0")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_7")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=1)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="上一轮回复")
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=2)
    chat_service.input_fallback_service.check_and_handle_nonsense = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    request = SimpleNamespace(accountId="user_7", question="你好", dialogId="dlg_7", sex=None)
    result = await chat_service.process_chat_request(request)

    assert result["success"] is True
    assert result["response"]
    assert any(token in result["response"] for token in ["在", "聊", "说", "问"])
    chat_service._call_ai.assert_not_awaited()


def test_ensure_humanlike_memory_ack_for_joking_user():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_joke")
    resp = chat_service._ensure_humanlike_memory_ack(
        "你查户口呢问这么细",
        profile,
        "方便留个电话号码吗？后续有合适的人选方便及时联系你~",
    )
    assert any(k in resp for k in ["了解", "匹配"])


def test_ensure_humanlike_memory_ack_reuses_location():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_loc")
    profile.location = "深圳"
    resp = chat_service._ensure_humanlike_memory_ack(
        "那边有什么好的相亲资源吗",
        profile,
        "我们这边有不少适配的优质单身资源哦，方便留个电话号码吗？",
    )
    assert any(k in resp for k in ["深圳", "那边"])


def test_ensure_humanlike_memory_ack_reuses_occupation_or_busy():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_job")
    profile.occupation = "运营"
    resp = chat_service._ensure_humanlike_memory_ack(
        "我工作比较忙",
        profile,
        "理解的，你方便留个电话号码吗？后续有合适的人选我们好及时联系到你~",
    )
    assert any(k in resp for k in ["运营", "工作", "忙"])


def test_ensure_humanlike_memory_ack_reuses_preference():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pref")
    profile.partner_requirement = "成熟稳重"
    resp = chat_service._ensure_humanlike_memory_ack(
        "有什么推荐吗",
        profile,
        "当然有呀，不过得先多了解点你的情况才能给你推更适配的人选哦。",
    )
    assert any(k in resp for k in ["成熟", "稳重", "合拍", "推荐"])


def test_select_model_for_turn_prefers_main_model_on_high_risk(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("电话不方便，留微信吧", "普通提示词")
    assert model == settings.model_name


def test_select_model_for_turn_uses_fast_model_on_low_complexity(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("怎么收费", "简短提示")
    assert model == "doubao-seed-fast"


def test_select_model_for_turn_falls_back_when_fast_model_missing(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.delenv("AI_FAST_MODEL_NAME", raising=False)
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("怎么收费", "简短提示")
    assert model == settings.model_name
