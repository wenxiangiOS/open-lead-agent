from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest

from src.config.settings import settings
from src.models.user_profile import UserProfile
from src.services.core.chat_service import ChatService
from src.services.prompts.prompts import get_main_dialogue


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    user_service = AsyncMock()
    return ChatService(_FakeAIService(), user_service)


def test_looks_like_fake_info_allows_partner_preference_sentence():
    chat_service = _build_chat_service()

    assert chat_service._looks_like_fake_info("身高高挑，不要超过30岁") is False


def test_looks_like_fake_info_detects_explicit_impossible_height():
    chat_service = _build_chat_service()

    assert chat_service._looks_like_fake_info("我是女生，今年1000岁，身高3米") is True


def test_extract_deterministic_profile_fields_handles_short_profile_answers():
    chat_service = _build_chat_service()

    extracted = chat_service._extract_deterministic_profile_fields("男的")
    assert extracted["sex"] == "男"

    extracted = chat_service._extract_deterministic_profile_fields("深圳")
    assert extracted["location"] == "深圳"

    extracted = chat_service._extract_deterministic_profile_fields("90后")
    assert extracted["age_label"] == "90后"
    assert extracted["age"] >= 30


def test_rule_profile_fast_path_stays_narrow_for_safe_short_answers():
    chat_service = _build_chat_service()

    assert chat_service._should_use_rule_profile_fast_path("深圳", {"location": "深圳"}, "model") is True
    assert chat_service._should_use_rule_profile_fast_path("为什么要电话", {"location": "深圳"}, "model") is False
    assert chat_service._should_use_rule_profile_fast_path("留微信可以吗", {"location": "深圳"}, "quick_faq") is False


def test_build_rule_profile_fast_response_asks_next_main_field_naturally():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_fast")
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    profile.age = 36
    profile.collection_progress["age"] = True

    response = chat_service._build_rule_profile_fast_response(profile, user_message="90后")

    assert "哪个城市" in response or "工作生活" in response


def test_get_main_dialogue_omits_irrelevant_strategy_lines():
    prompt = get_main_dialogue(
        gender_instruction="用户性别未知",
        collected_info="男,90后",
        missing_fields="所在地、学历",
        current_main_target="所在地",
        current_side_target="无",
        user_type="配合型",
        can_enter_contact=False,
        is_first_chat=False,
    )

    assert "顺带字段：无" not in prompt
    assert "用户类型：配合型" not in prompt
    assert "当前不要主动切到电话或微信" in prompt


@pytest.mark.anyio
async def test_handle_contact_validation_accepts_phone_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_1")
    chat_service.validation_service.validate_contact = AsyncMock(return_value=(True, None, None))
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.contact_service.get_next_action = lambda _profile, _message="": SimpleNamespace(value="none")
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

    request = SimpleNamespace(accountId="user_2", question="我已经结婚了", dialogId="dlg_1", sex=None, timestamp=None)

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
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: True
    chat_service.contact_service.get_next_action = lambda _profile, _message="": SimpleNamespace(value="none")
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
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=3)
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.input_fallback_service.check_and_handle_nonsense = AsyncMock(return_value="兜底回复")

    request = SimpleNamespace(accountId="user_5", question="你好", dialogId="dlg_2", sex=None, timestamp=None)

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

    request = SimpleNamespace(accountId="user_6", question="你好", dialogId="dlg_3", sex="女", timestamp=None)
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

    request = SimpleNamespace(accountId="user_7", question="你好", dialogId="dlg_7", sex=None, timestamp=None)
    result = await chat_service.process_chat_request(request)

    assert result["success"] is True
    assert result["response"]
    assert any(token in result["response"] for token in ["在", "聊", "说", "问"])
    chat_service._call_ai.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_short_circuits_risk_guard_before_ai():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_risk")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=1)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={})
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=2)
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.conversation_rule_service.try_handle = AsyncMock(
        return_value=SimpleNamespace(handled=False, response_payload=None)
    )
    chat_service._handle_refusal_detection = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    request = SimpleNamespace(accountId="user_risk", question="我最近活不下去了", dialogId="dlg_risk", sex=None, timestamp=None)
    result = await chat_service.process_chat_request(request)

    assert "先保证安全" in result["response"]
    chat_service._call_ai.assert_not_awaited()
    chat_service._handle_refusal_detection.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_boundary_pause_does_not_collect_or_call_ai():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_boundary_pause")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=1)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={})
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=2)
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.conversation_rule_service.try_handle = AsyncMock(
        return_value=SimpleNamespace(handled=False, response_payload=None)
    )
    chat_service._handle_refusal_detection = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    request = SimpleNamespace(
        accountId="user_boundary_pause",
        question="电话先不方便留，我先不留",
        dialogId="dlg_boundary",
        sex=None,
        timestamp=None,
    )
    result = await chat_service.process_chat_request(request)

    assert "先不追问" in result["response"]
    chat_service._handle_refusal_detection.assert_awaited_once()
    chat_service._call_ai.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_prefers_quick_faq_over_boundary_pause():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_faq_boundary")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.user_service.get_user_preference = AsyncMock(return_value={})
    chat_service.user_service.update_user_preference = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=1)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={})
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=2)
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.conversation_rule_service.try_handle = AsyncMock(
        return_value=SimpleNamespace(handled=False, response_payload=None)
    )
    chat_service._handle_refusal_detection = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="不该调用")

    request = SimpleNamespace(accountId="user_faq_boundary", question="你们靠谱吗", dialogId="dlg_faq", sex=None, timestamp=None)
    result = await chat_service.process_chat_request(request)

    assert "安全" in result["response"] or "靠谱" in result["response"] or "真人审核" in result["response"]
    assert "先不追问" not in result["response"]
    chat_service._call_ai.assert_not_awaited()


@pytest.mark.anyio
async def test_process_chat_request_prefers_contact_switch_over_boundary_pause():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_contact_switch")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=1)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={})
    chat_service.dialogue_manager.add_to_history = AsyncMock(return_value=None)
    chat_service.dialogue_manager.update_recent_responses = AsyncMock(return_value=None)
    chat_service.dialogue_manager.increment_message_count = AsyncMock(return_value=2)
    chat_service.input_fallback_service.reset_nonsense_count = AsyncMock(return_value=None)
    chat_service.conversation_rule_service.try_handle = AsyncMock(
        return_value=SimpleNamespace(handled=False, response_payload=None)
    )
    chat_service._handle_refusal_detection = AsyncMock(return_value=None)
    chat_service._call_ai = AsyncMock(return_value="")
    chat_service.extraction_service.extract_json_from_response = lambda _text: {}
    chat_service._handle_contact_validation = AsyncMock(return_value="可以呀，那你直接发我微信号就行，我这边先记下来～")
    chat_service.profile_collection_coordinator.process_collection = AsyncMock(
        return_value=SimpleNamespace(collection_result={"collected": False, "all_fields": []})
    )
    chat_service.profile_collection_coordinator.build_contact_decision = lambda *_args, **_kwargs: None
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: True

    request = SimpleNamespace(accountId="user_contact_switch", question="电话不方便，留微信可以吗", dialogId="dlg_contact", sex=None, timestamp=None)
    result = await chat_service.process_chat_request(request)

    assert "微信号" in result["response"] or "微信" in result["response"]
    assert "先不追问" not in result["response"]
    chat_service._call_ai.assert_awaited_once()


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


def test_select_model_for_turn_uses_fast_model_for_safe_short_profile_answer_with_medium_prompt(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("深圳", "x" * 6000)

    assert model == "doubao-seed-fast"


def test_select_model_for_turn_keeps_main_model_for_safe_short_profile_answer_with_very_long_prompt(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("深圳", "x" * 7000)

    assert model == settings.model_name


def test_get_risk_guard_response_handles_self_harm_without_collection():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_risk")

    response = chat_service._get_risk_guard_response("我最近真的活不下去了", profile)

    assert response is not None
    assert "先保证安全" in response
    assert "立刻联系" in response or "热线" in response
    assert "电话" not in response
    assert "微信" not in response


def test_get_risk_guard_response_handles_private_contact_boundary():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_boundary")

    response = chat_service._get_risk_guard_response("你直接把你私人微信给我", profile)

    assert response is not None
    assert "不方便" in response
    assert "按流程" in response or "合规" in response
    assert "年龄" not in response
    assert "城市" not in response


def test_get_boundary_pause_response_handles_privacy_concern():
    chat_service = _build_chat_service()
    response = chat_service._get_boundary_pause_response("这个我不太方便说，先不留")
    assert response is not None
    assert "先不追问" in response
    assert "隐私" in response or "流程" in response


def test_apply_field_ask_guard_blocks_cooldown_field_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_1")
    profile.recent_asked_fields = ["age"]

    response = chat_service._apply_field_ask_guard(profile, "没问题～那你今年多大呀？")

    assert "多大" not in response
    assert "年龄" not in response


def test_apply_field_ask_guard_blocks_over_limit_field_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_2")
    profile.field_ask_count = {"location": 2}

    response = chat_service._apply_field_ask_guard(profile, "好的，那你现在在哪个城市工作生活呢？")

    assert "哪个城市" not in response
    assert "工作生活" not in response


def test_build_rotating_ending_message_avoids_same_as_last(monkeypatch):
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_end_rotate")

    monkeypatch.setattr("src.services.core.chat_service.random.choice", lambda seq: seq[0])
    first = chat_service._build_rotating_ending_message(profile, "")
    second = chat_service._build_rotating_ending_message(profile, first)

    assert first
    assert second
    assert second != first


def test_build_rotating_ending_message_contains_timeline_text(monkeypatch):
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_end_timeline")

    monkeypatch.setattr("src.services.core.chat_service.random.choice", lambda seq: seq[0])
    response = chat_service._build_rotating_ending_message(profile, "")

    assert response
    assert "联系前" in response or "约时间" in response


def test_apply_dialogue_style_guard_trims_redundant_ack_prefix():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_ack_guard")
    guarded = chat_service._apply_dialogue_style_guard(
        "收到啦，我记下了～",
        "收到啦，本科学历我记下了～想问下你现在是做哪方面工作的呀？",
        profile,
    )
    assert not guarded.startswith("收到啦")
    assert "工作的呀" in guarded


def test_apply_dialogue_style_guard_enforces_field_interleaving_with_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_partner")
    profile.recent_asked_fields = ["sex", "age", "education"]

    guarded = chat_service._apply_dialogue_style_guard(
        "那你是什么学历呀？",
        "好的，那你现在在哪个城市生活呀？",
        profile,
    )

    assert "偏好" in guarded or "看重" in guarded or "喜欢什么样" in guarded


def test_apply_dialogue_style_guard_enforces_field_interleaving_with_income_when_partner_done():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_income")
    profile.recent_asked_fields = ["age", "education", "occupation"]
    profile.partner_requirement = "成熟稳重"
    profile.collection_progress["partner_requirement"] = True
    profile.occupation = "IT"

    guarded = chat_service._apply_dialogue_style_guard(
        "你现在是做哪方面工作的呀？",
        "顺带问下你现在是单身状态在认真了解吗？",
        profile,
    )

    assert "月收入" in guarded or "收入" in guarded
    assert "不方便说也没关系" in guarded


def test_apply_dialogue_style_guard_breaks_repeat_loop_with_clarification_request():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_repeat_break")

    guarded = chat_service._apply_dialogue_style_guard(
        "我们先不连着问资料，你也可以先说说你更在意的匹配点。",
        "我们先不连着问资料，你也可以先说说你更在意的匹配点。",
        profile,
        user_message="匹配点是啥意思，解释下",
    )

    assert guarded != "我们先不连着问资料，你也可以先说说你更在意的匹配点。"
    assert any(marker in guarded for marker in ["换个直白", "匹配点", "比如"])


def test_apply_dialogue_style_guard_blocks_confirm_word_contact_misroute():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_confirm_guard")

    guarded = chat_service._apply_dialogue_style_guard(
        "你更想先聊哪边？",
        "你这边资料我先整理好了，后续方便联系推进，方便留个电话吗？",
        profile,
        user_message="好的",
    )

    assert "留个电话" not in guarded
    assert "不急着留联系方式" in guarded


def test_apply_dialogue_style_guard_avoids_preference_hard_ending():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pref_guard")

    guarded = chat_service._apply_dialogue_style_guard(
        "你想找什么类型？",
        "谢谢你的坦诚呀，我们这边主要做异性相亲服务，祝你好运～",
        profile,
        user_message="我是les，喜欢女生",
    )

    assert "祝你" not in guarded


def test_infer_contact_attempt_from_context_does_not_treat_wechat_intent_as_wechat_id():
    chat_service = _build_chat_service()

    value, contact_type = chat_service._infer_contact_attempt_from_context("用微信联系吧", "ask_wechat")

    assert value is None
    assert contact_type is None


def test_apply_extraction_guards_prioritizes_sex_answer_in_sex_question_context():
    chat_service = _build_chat_service()
    extracted = {"partner_requirement": "找男性"}

    guarded = chat_service._apply_extraction_guards(
        extracted,
        user_message="你们男的",
        last_response="你是男生还是女生呀？",
    )

    assert guarded.get("sex") == "男"
    assert "partner_requirement" not in guarded


def test_build_turn_decision_returns_structured_fields_for_clarification():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_decision")
    decision = chat_service._build_turn_decision(
        "匹配点是啥意思，解释下",
        profile,
        conversation_context={"message_count": 3},
    )

    assert decision.intent == "clarification"
    assert decision.response_channel == "quick_faq"
    assert isinstance(decision.tone_policy, dict)
    assert "core_streak_max" in decision.tone_policy


def test_fuse_extracted_fields_prefers_rule_for_critical_conflict():
    chat_service = _build_chat_service()
    fused, meta = chat_service._fuse_extracted_fields(
        ai_extracted={"sex": "女", "occupation": "产品"},
        rule_extracted={"sex": "男", "occupation": "运营"},
        user_message="男的，我是做运营的",
    )

    assert fused["sex"] == "男"
    assert meta["sex"]["source"] == "rule_override"
    assert fused["occupation"] == "产品"
    assert meta["occupation"]["source"] == "ai_preferred"


@pytest.mark.parametrize(
    ("user_input", "expected_keyword"),
    [
        ("我抑郁了该吃什么药", "不适合"),
        ("这个事情要怎么起诉对方", "律师"),
        ("你是AI吗", "流程"),
        ("你烦不烦，闭嘴", "不追问"),
    ],
)
def test_get_risk_guard_response_covers_other_high_risk_categories(user_input, expected_keyword):
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_risk_multi")

    response = chat_service._get_risk_guard_response(user_input, profile)

    assert response is not None
    assert expected_keyword in response
    assert "电话" not in response
    assert "微信" not in response


def test_select_model_for_turn_falls_back_when_fast_model_missing(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.delenv("AI_FAST_MODEL_NAME", raising=False)
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("怎么收费", "简短提示")
    assert model == settings.model_name


@pytest.mark.anyio
async def test_call_ai_returns_empty_when_hard_timeout_triggered(monkeypatch):
    chat_service = _build_chat_service()

    async def _slow_generate_response(*args, **kwargs):
        import asyncio
        await asyncio.sleep(1.0)
        return "不该返回"

    monkeypatch.setenv("CHAT_AI_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("CHAT_AI_HARD_TIMEOUT_SECONDS", "0.6")
    chat_service.ai_service.generate_response = AsyncMock(side_effect=_slow_generate_response)

    result = await chat_service._call_ai("prompt", "timeout_user", "你好")

    assert result == ""


@pytest.mark.anyio
async def test_build_no_ai_response_does_not_repeat_same_phone_ask_consecutively():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_no_ai_repeat")
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="方便留个电话吗？后续有合适的人选时联系你～")
    chat_service.contact_service.get_next_action = lambda _profile, _message="": SimpleNamespace(value="ask_phone")

    response = await chat_service._build_no_ai_response("user_no_ai_repeat", profile, "这个为啥要问")

    assert "方便留个电话" not in response
    assert "不重复" in response


@pytest.mark.anyio
async def test_build_no_ai_response_adds_transition_before_contact_ask_when_profile_ready():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_transition_ready")
    profile.sex = "男"
    profile.age = 30
    profile.education = "本科"
    profile.occupation = "IT"
    profile.location = "深圳"
    profile.marital_status = "单身"
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="收到，你现在是单身状态")
    chat_service.contact_service.get_next_action = lambda _profile, _message="": SimpleNamespace(value="ask_phone")
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: True

    response = await chat_service._build_no_ai_response("user_transition_ready", profile, "好的")

    assert "方便留个电话" in response
    assert any(marker in response for marker in ["资料我先整理好了", "后续为了方便联系推进"])


@pytest.mark.anyio
async def test_get_user_conversation_history_awaits_user_service_and_normalizes_payload():
    chat_service = _build_chat_service()
    chat_service.user_service.get_conversation_history = AsyncMock(
        return_value={
            "user_id": "u_hist",
            "conversations": [{"user_message": "你好", "assistant_response": "你好呀"}],
            "total_count": 7,
            "limit": 10,
            "offset": 0,
        }
    )

    result = await chat_service.get_user_conversation_history("u_hist", limit=10, offset=0)

    assert result["success"] is True
    assert result["history"] == [{"user_message": "你好", "assistant_response": "你好呀"}]
    assert result["total"] == 7
    chat_service.user_service.get_conversation_history.assert_awaited_once_with("u_hist", 10, 0)


def test_legacy_service_packages_use_lazy_exports_without_import_cycle():
    services_pkg = importlib.import_module("src.services")
    data_pkg = importlib.import_module("src.services.data")

    extraction_cls = getattr(data_pkg, "ExtractionService")
    chat_cls = getattr(services_pkg, "ChatService")

    assert extraction_cls.__name__ == "ExtractionService"
    assert chat_cls.__name__ == "ChatService"
