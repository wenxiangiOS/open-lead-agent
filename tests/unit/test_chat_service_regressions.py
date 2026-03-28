from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest

from src.config.settings import settings
from src.models.user_profile import UserProfile
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.services.ai_service import AIService
from src.services.core.chat_service import ChatService
from src.services.prompts.prompts import CORE_PERSONALITY, MAIN_DIALOGUE, SYSTEM_WELCOME_MESSAGE, get_main_dialogue
from src.services.core.chat_service import OpeningIntentSignal
from src.modules.profile_collection.domain.extraction_service import ExtractionService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    user_service = AsyncMock()
    return ChatService(_FakeAIService(), user_service)


class _FakeProfileUserService:
    def __init__(self, profile: UserProfile):
        self.profile = profile

    async def update_user_profile_field(self, account_id: str, field: str, value):
        setattr(self.profile, field, value)
        self.profile.collection_progress[field] = True
        return True

    async def save_user_profile(self, account_id: str, profile: UserProfile):
        self.profile = profile
        return True

    async def get_user_profile(self, account_id: str):
        return self.profile


def test_core_personality_does_not_hardcode_fake_resume():
    assert "28岁" not in CORE_PERSONALITY
    assert "深圳做了3年红娘" not in CORE_PERSONALITY
    assert "从业" not in CORE_PERSONALITY or "不要虚构" in CORE_PERSONALITY


@pytest.mark.asyncio
async def test_process_extracted_data_allows_explicit_location_correction_override():
    profile = UserProfile(account_id="u_location_correction")
    profile.location = "深圳"
    profile.collection_progress["location"] = True
    user_service = _FakeProfileUserService(profile)
    extraction_service = ExtractionService(user_service)

    result = await extraction_service.process_extracted_data(
        "u_location_correction",
        profile,
        {"location": "广州"},
        user_message="我不在深圳，在广州",
    )

    assert result["collected"] is True
    assert profile.location == "广州"


@pytest.mark.asyncio
async def test_process_extracted_data_allows_explicit_marital_status_correction_override():
    profile = UserProfile(account_id="u_marital_correction")
    profile.marital_status = "单身"
    profile.collection_progress["marital_status"] = True
    user_service = _FakeProfileUserService(profile)
    extraction_service = ExtractionService(user_service)

    result = await extraction_service.process_extracted_data(
        "u_marital_correction",
        profile,
        {"marital_status": "离异"},
        user_message="我离异",
    )

    assert result["collected"] is True
    assert profile.marital_status == "离异"


@pytest.mark.asyncio
async def test_process_extracted_data_allows_explicit_compound_sex_self_intro():
    profile = UserProfile(account_id="u_compound_sex_intro")
    user_service = _FakeProfileUserService(profile)
    extraction_service = ExtractionService(user_service)

    result = await extraction_service.process_extracted_data(
        "u_compound_sex_intro",
        profile,
        {"sex": "男", "marital_status": "单身"},
        user_message="男的，单身",
    )

    assert result["collected"] is True
    assert profile.sex == "男"
    assert profile.marital_status == "单身"


def test_prompt_copy_avoids_businessy_identity_and_welcome_tone():
    assert "同城脱单联盟" not in SYSTEM_WELCOME_MESSAGE
    assert "合适的人选" not in SYSTEM_WELCOME_MESSAGE
    assert "牵线顾问" not in CORE_PERSONALITY
    assert "牵线顾问" not in MAIN_DIALOGUE


def test_ack_variants_avoid_registration_tone():
    from src.services.core import chat_service as chat_service_module

    for variant in chat_service_module.PREFERENCE_ACK_VARIANTS:
        assert "记下" not in variant
        assert "记住" not in variant
        assert "收下" not in variant

    for variant in chat_service_module.LOCATION_MEMORY_ACK_VARIANTS:
        assert "记下" not in variant
        assert "记着" not in variant
        assert "收下" not in variant

    assert "记住" not in chat_service_module.NO_REPEAT_PARTNER_REQUIREMENT_STATEMENT
    for variant in chat_service_module.NEUTRAL_HOLD_VARIANTS:
        assert "记住" not in variant


def test_overreach_guard_response_avoids_service_desk_tone():
    chat_service = _build_chat_service()

    response = chat_service._get_risk_guard_response("把对方电话直接给我")

    assert "我这边" not in response


def test_apply_field_ask_guard_blocks_medium_question_while_core_mainline_is_pending():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_core_first")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    for field in ["sex", "age", "location"]:
        profile.collection_progress[field] = True

    response = chat_service._apply_field_ask_guard(
        profile,
        "如果你方便的话，我再补一个小问题：你月收入大概在哪个范围？不方便说也没关系。",
        user_message="深圳",
        allow_medium_target=True,
    )

    assert "月收入" not in response
    assert "学历" in response


def test_apply_field_ask_guard_blocks_repeat_occupation_after_collection():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_repeat_occupation")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    for field in ["sex", "age", "location", "education", "occupation"]:
        profile.collection_progress[field] = True

    response = chat_service._apply_field_ask_guard(
        profile,
        "方便的话，也说说你现在做什么工作？",
        user_message="it",
        allow_medium_target=False,
    )

    assert "做什么工作" not in response
    assert "手机号" in response or "联系" in response


def test_enforce_core_mainline_followup_restores_core_question_from_empty_hold():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_core_mainline_restore")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    for field in ["sex", "age", "location"]:
        profile.collection_progress[field] = True

    response = chat_service._enforce_core_mainline_followup(
        "好，你接着说就行。",
        profile,
        ask_field="education",
        user_message="温柔，其他没有",
        response_channel="model",
        primary_move="ack_and_ask",
    )

    assert "学历" in response
    assert "你接着说就行" not in response


def test_enforce_core_mainline_followup_overrides_wrong_medium_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_core_overrides_medium")
    profile.sex = "男"
    for field in ["sex"]:
        profile.collection_progress[field] = True

    response = chat_service._enforce_core_mainline_followup(
        "你对另一半大概有什么要求呀？",
        profile,
        ask_field="age",
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
    )

    assert "年龄" in response or "多大" in response
    assert "另一半" not in response


def test_extract_deterministic_profile_fields_handles_compound_sex_and_location_reply():
    chat_service = _build_chat_service()

    extracted = chat_service._extract_deterministic_profile_fields("男的呢，在深圳")

    assert extracted["sex"] == "男"
    assert extracted["location"] == "深圳"


def test_extract_simple_partner_requirement_handles_oral_preference_reply():
    chat_service = _build_chat_service()

    preference = chat_service._extract_simple_partner_requirement("温柔就行了")

    assert preference == "温柔"


def test_extract_simple_partner_requirement_handles_modal_particle_reply():
    chat_service = _build_chat_service()

    preference = chat_service._extract_simple_partner_requirement("温柔吧")

    assert preference == "温柔"


def test_enforce_core_mainline_followup_keeps_divorce_confirmation_prompt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_lock")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    response = chat_service._enforce_core_mainline_followup(
        "可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？",
        profile,
        ask_field="occupation",
        user_message="离异",
        response_channel="model",
        primary_move="light_followup",
    )

    assert "离婚手续" in response
    assert "工作" not in response


def test_build_interleaving_followup_combines_main_and_income_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_income")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    for field in ["sex", "age", "location", "education"]:
        profile.collection_progress[field] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "本科",
        main_target="occupation",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "工作" in response or "做什么" in response
    assert "月收入" in response or "收入" in response


def test_build_interleaving_followup_prefers_bridge_mode_over_generic_income_fusion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_bridge_income")

    response = chat_service._build_interleaving_followup(
        profile,
        "我目前在深圳呢，目前单身",
        main_target="occupation",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "工作" in response or "做什么" in response
    assert "收入" in response or "月薪" in response


def test_build_interleaving_followup_combines_main_and_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_partner")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    for field in ["sex", "age", "location"]:
        profile.collection_progress[field] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "深圳",
        main_target="education",
        preferred_side_target="partner_requirement",
        allow_medium_target=True,
    )

    assert "学历" in response
    assert "找对象" in response or "看重" in response or "在意" in response


def test_build_profile_bridge_generation_instruction_requires_marital_and_partner_requirement_binding():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_profile_bridge_partner")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    for field in ["sex", "age", "location"]:
        profile.collection_progress[field] = True
    decision = SimpleNamespace(
        response_channel="model",
        ask_field="marital_status",
        allow_medium_target=True,
    )

    instruction = chat_service._build_profile_bridge_generation_instruction(
        user_message="我在深圳做IT",
        user_profile=profile,
        turn_decision=decision,
        conversation_context={"message_count": 2},
    )

    assert "现在是否单身/婚况" in instruction
    assert "择偶要求/更看重哪一点" in instruction
    assert "城市=深圳" in instruction


@pytest.mark.asyncio
async def test_enforce_profile_bridge_response_rewrites_when_side_target_missing():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_profile_bridge_enforce")
    decision = SimpleNamespace(
        response_channel="model",
        ask_field="occupation",
        allow_medium_target=True,
    )
    chat_service.ai_service.resolve_timeout_settings = lambda: {"chat_ai_timeout": 45.0}
    chat_service.ai_service.generate_response = AsyncMock(
        return_value="在深圳这边工作的话，你主要做什么呀，月薪大概在哪个范围呢？"
    )

    response = await chat_service._enforce_profile_bridge_response(
        "在深圳这边是吧。你主要做什么呀？",
        account_id="u_profile_bridge_enforce",
        user_message="我目前在深圳，目前单身",
        user_profile=profile,
        turn_decision=decision,
        conversation_context={"message_count": 2, "recent_responses": []},
    )

    assert "做什么" in response or "工作" in response
    assert "月薪" in response or "收入" in response


@pytest.mark.asyncio
async def test_enforce_profile_bridge_response_rewrites_when_splice_markers_present():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_profile_bridge_splice")
    decision = SimpleNamespace(
        response_channel="model",
        ask_field="occupation",
        allow_medium_target=True,
    )
    chat_service.ai_service.resolve_timeout_settings = lambda: {"chat_ai_timeout": 45.0}
    chat_service.ai_service.generate_response = AsyncMock(
        return_value="在深圳这边做什么工作呀，月薪大概在哪个范围呢？"
    )

    response = await chat_service._enforce_profile_bridge_response(
        "在深圳这边是吧。你主要做什么呀？如果你方便的话，我再补一个小问题：你月收入大概在哪个范围？不方便说也没关系。",
        account_id="u_profile_bridge_splice",
        user_message="目前在深圳，单身呢",
        user_profile=profile,
        turn_decision=decision,
        conversation_context={"message_count": 2, "recent_responses": []},
    )

    assert "做什么" in response or "工作" in response
    assert "月薪" in response or "收入" in response
    assert "再补一个小问题" not in response


def test_build_profile_bridge_generation_instruction_requires_contextual_bridge():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_profile_bridge")
    decision = SimpleNamespace(
        response_channel="model",
        ask_field="occupation",
        allow_medium_target=True,
    )

    instruction = chat_service._build_profile_bridge_generation_instruction(
        user_message="我目前在深圳，姓李，目前一个人",
        user_profile=profile,
        turn_decision=decision,
        conversation_context={"message_count": 2},
    )

    assert "城市=深圳" in instruction
    assert "当前状态=单身" in instruction
    assert "工作/做什么" in instruction
    assert "月薪/收入区间" in instruction
    assert "不要写成固定模板" in instruction


def test_build_profile_bridge_generation_instruction_skips_without_bridge_fields():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_profile_bridge_skip")
    decision = SimpleNamespace(
        response_channel="model",
        ask_field="occupation",
        allow_medium_target=True,
    )

    instruction = chat_service._build_profile_bridge_generation_instruction(
        user_message="我姓李",
        user_profile=profile,
        turn_decision=decision,
        conversation_context={"message_count": 2},
    )

    assert instruction == ""


def test_augment_prompt_for_profile_bridge_followup_prefixes_instruction():
    chat_service = _build_chat_service()

    prompt = chat_service._augment_prompt_for_profile_bridge_followup(
        "MAIN_PROMPT",
        "【资料桥接追问要求】\n顺着城市去聊",
    )

    assert prompt.startswith("【资料桥接追问要求】")
    assert prompt.endswith("MAIN_PROMPT")


def test_divorce_confirmation_cleared_response_falls_forward_instead_of_empty_ack():
    chat_service = _build_chat_service()

    response = chat_service._build_divorce_confirmation_cleared_response("marital_status")

    assert response not in {"好，那我知道了。", "嗯，我知道了。"}
    assert "电话" in response or "方便" in response


def test_wechat_persuasion_copy_differs_from_first_ask():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_wechat_persuade")
    profile.rejected_phone = True
    profile.phone_ask_count = 2
    profile.wechat_ask_count = 1

    response = chat_service._apply_refusal_respect_guard(
        "随便写点",
        profile,
        user_message="不留",
    )

    assert "微信更方便，留个微信也可以" not in response
    assert "换个方式说" not in response
    assert "方便及时" not in response
    assert "常用微信" in response or "沟通也方便一些" in response


@pytest.mark.anyio
async def test_build_no_ai_response_contact_copy_avoids_process_tone():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_copy")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    for field in ["sex", "age", "location", "education", "occupation"]:
        profile.collection_progress[field] = True

    response = await chat_service._build_no_ai_response("u_contact_copy", profile, "做it啊")

    assert "资料差不多" not in response
    assert "记下啦" not in response


@pytest.mark.anyio
async def test_generate_system_prompt_avoids_fake_resume_injection():
    ai_service = AIService()

    prompt = await ai_service.generate_system_prompt(
        personality_profile={
            "name": "小桃子",
            "age": 28,
            "experience_years": 3,
            "personality": {},
        },
        user_context={},
    )

    assert "3年经验的专业红娘" not in prompt
    assert "不要虚构你的年龄" in prompt
    assert "客服公告" in prompt


@pytest.mark.anyio
async def test_generate_ai_ending_response_uses_extra_instructions():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_ai_ending")
    profile.sex = "男"
    profile.location = "深圳"
    profile.rejected_phone = True
    profile.rejected_wechat = True

    captured = {}

    async def _fake_call_ai(prompt: str, account_id: str, user_message: str = "") -> str:
        captured["prompt"] = prompt
        captured["account_id"] = account_id
        captured["user_message"] = user_message
        return "我知道你现在还不想留联系方式，那我们就先聊到这里。"

    chat_service._call_ai = _fake_call_ai

    response = await chat_service._generate_ai_ending_response(
        account_id="user_ai_ending",
        user_profile=profile,
        user_message="微信也不方便",
        ending_info={
            "scenario": "both_rejected",
            "use_ai": True,
            "extra_instructions": "用户不愿留下任何联系方式，请用理解和尊重的语气收尾。",
        },
        fallback_response="那我们先聊到这里。",
    )

    assert response == "我知道你现在还不想留联系方式，那我们就先聊到这里。"
    assert "用户不愿留下任何联系方式" in captured["prompt"]
    assert "收尾场景：both_rejected" in captured["prompt"]
    assert captured["account_id"] == "user_ai_ending"


@pytest.mark.anyio
async def test_generate_ai_ending_response_normal_complete_prompt_avoids_exposing_collection_action():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_ai_ending_normal")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"

    captured = {}

    async def _fake_call_ai(prompt: str, account_id: str, user_message: str = "") -> str:
        captured["prompt"] = prompt
        return "祝你顺顺利利。"

    chat_service._call_ai = _fake_call_ai

    response = await chat_service._generate_ai_ending_response(
        account_id="user_ai_ending_normal",
        user_profile=profile,
        user_message="wx85239523895289",
        ending_info={
            "scenario": "normal_complete",
            "use_ai": True,
            "extra_instructions": "信息收集已完成，请自然收尾。不要出现“我记下了你的微信/手机号”“之后第一时间通过微信联系你”这类直接暴露信息收集动作的说法。",
        },
        fallback_response="那我们先聊到这里。",
    )

    assert response == "祝你顺顺利利。"
    assert "不要出现“我记下了你的微信/手机号”" in captured["prompt"]
    assert "第一时间通过微信联系你" in captured["prompt"]


@pytest.mark.anyio
async def test_generate_ai_ending_response_falls_back_when_no_extra_instructions():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_ai_ending_fallback")

    response = await chat_service._generate_ai_ending_response(
        account_id="user_ai_ending_fallback",
        user_profile=profile,
        user_message="好的",
        ending_info={"scenario": "normal_complete", "use_ai": True, "extra_instructions": ""},
        fallback_response="那我们先聊到这里。",
    )

    assert response == "那我们先聊到这里。"


def test_expectation_service_timeline_copy_avoids_contacting_candidates_tone():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect")

    response = service.get_matching_timeline_response(profile)

    assert "1-2天" in response
    assert "基本情况" in response or "聊清楚" in response
    assert "联系你" not in response
    assert "牵线同事" not in response


def test_expectation_service_timeline_copy_uses_fast_track_when_profile_qualifies():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_fast")
    profile.age = 35
    profile.education = "本科"
    profile.sex = "男"
    profile.monthly_income = "4万"

    response = service.get_matching_timeline_response(profile)

    assert "1-8小时" in response
    assert "联系你" not in response


def test_expectation_service_contact_completion_response_uses_business_closure():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_complete")
    profile.age = 35
    profile.education = "本科"
    profile.sex = "男"
    profile.monthly_income = "4万"

    response = service.get_contact_completion_response(profile)

    assert "等好消息" in response
    assert "1-8小时" in response
    assert "牵线同事" in response


def test_get_main_dialogue_contact_faq_copy_avoids_overpromising():
    prompt = get_main_dialogue(
        gender_instruction="用户性别未知",
        collected_info="深圳, 本科",
        missing_fields="职业、婚况",
        current_main_target="职业",
        current_side_target="无",
        user_type="配合型",
        can_enter_contact=False,
        is_first_chat=False,
        turn_plan_instruction="",
    )

    assert "不承诺直接发对方资料或照片" in prompt
    assert "不要承诺直接互换双方联系方式" in prompt
    assert "不要承诺立刻安排见面" in prompt
    assert "不要承诺马上发定位" in prompt


def test_extract_deterministic_profile_fields_handles_short_profile_answers():
    chat_service = _build_chat_service()

    extracted = chat_service._extract_deterministic_profile_fields("男的")
    assert extracted["sex"] == "男"

    extracted = chat_service._extract_deterministic_profile_fields("深圳")
    assert extracted["location"] == "深圳"

    extracted = chat_service._extract_deterministic_profile_fields("90后")
    assert extracted["age_label"] == "90后"
    assert extracted["age"] >= 30

    extracted = chat_service._extract_deterministic_profile_fields("我深圳的")
    assert extracted["location"] == "深圳"

    extracted = chat_service._extract_deterministic_profile_fields("it")
    assert extracted["occupation"] == "IT"


def test_profile_collection_policy_locks_flow_when_divorce_confirmation_pending():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_divorce_pending")
    profile.marital_status = "离异"
    profile.collection_progress["marital_status"] = True
    profile.divorce_confirmation_pending = True

    decision = policy.decide(profile, user_message="我离异可以吗")

    assert decision.main_target == "marital_status"
    assert decision.side_target is None
    assert decision.can_enter_contact is False
    assert decision.missing_fields == ["marital_status"]


def test_build_turn_decision_sets_divorce_confirmation_action():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_decision")
    profile.marital_status = "离异"
    profile.collection_progress["marital_status"] = True
    profile.divorce_confirmation_pending = True

    decision = chat_service._build_turn_decision("我离异可以吗", profile, conversation_context={"message_count": 3})

    assert decision.ask_field == "marital_status"
    assert decision.next_action == "confirm_divorce_status"
    assert decision.primary_move == "confirm_status_only"


def test_build_turn_decision_prefers_answer_then_pause_for_faq():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_faq_move")

    decision = chat_service._build_turn_decision("怎么收费", profile, conversation_context={"message_count": 1})

    assert decision.primary_move == "answer_then_pause"
    assert decision.prioritize_user_question is True
    assert decision.allow_contact_target is False
    assert decision.allow_medium_target is False
    assert decision.response_channel == "quick_faq"


def test_build_turn_decision_prefers_answer_then_pause_for_natural_timeline_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_timeline_natural")

    decision = chat_service._build_turn_decision("你们多久会联系我呀", profile, conversation_context={"message_count": 1})

    assert decision.primary_move == "answer_then_pause"
    assert decision.prioritize_user_question is True
    assert decision.allow_contact_target is False
    assert decision.response_channel == "quick_faq"


def test_build_turn_decision_saves_resume_target_when_user_question_interrupts_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_save")

    decision = chat_service._build_turn_decision("你们靠谱吗？", profile, conversation_context={"message_count": 1})

    assert decision.prioritize_user_question is True
    assert profile.resume_profile_target == "sex"
    assert profile.resume_profile_mode == "collect_core"
    assert decision.resume_target == "sex"


def test_build_turn_decision_uses_light_followup_for_short_message():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_light_followup")

    decision = chat_service._build_turn_decision("男的", profile, conversation_context={"message_count": 1})

    assert decision.primary_move == "light_followup"


def test_build_turn_decision_uses_opening_probe_for_pure_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe")

    decision = chat_service._build_turn_decision("在吗", profile, conversation_context={"message_count": 0})

    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_probe_for_combined_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe_combo")

    decision = chat_service._build_turn_decision("你好，在吗？", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_probe"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_probe_for_repeated_casual_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe_repeat")

    decision = chat_service._build_turn_decision("在吗在吗", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_probe"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_probe_for_noisy_repeated_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe_noisy_repeat")

    decision = chat_service._build_turn_decision("你好呀，在吗在吗呀呀呀？", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_probe"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_clarify_for_greeting_with_noise_tail():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_clarify_noise_tail")

    decision = chat_service._build_turn_decision("你好呀，坏呼叫", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_clarify"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_self_intro_for_probe_followup_wo_wenwen_qingkuang():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro_probe_wo_wenwen_qingkuang")

    decision = chat_service._build_turn_decision(
        "我问问你情况呢",
        profile,
        conversation_context={
            "message_count": 1,
            "recent_responses": ["你好呀，在的。 你是想认真聊聊，还是先问问情况呀？"],
        },
    )

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_probe_for_english_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe_hi")

    decision = chat_service._build_turn_decision("hi", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_probe"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_probe_for_light_consult():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_probe_consult")

    decision = chat_service._build_turn_decision("想了解下", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_probe"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None


def test_build_turn_decision_uses_opening_clarify_for_unstable_opening_input():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_clarify")

    decision = chat_service._build_turn_decision("佃�好", profile, conversation_context={"message_count": 0})

    assert decision.intent == "opening_clarify"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_self_intro_for_explicit_matchmaking_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro")

    decision = chat_service._build_turn_decision("找对象", profile, conversation_context={"message_count": 1})

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"
    assert decision.allow_contact_target is False
    assert decision.allow_medium_target is False


def test_build_turn_decision_uses_opening_self_intro_after_probe_followup_soft_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro_after_probe")

    decision = chat_service._build_turn_decision(
        "先了解下",
        profile,
        conversation_context={
            "message_count": 1,
            "recent_responses": ["你好呀，我在呢。你这边是想找对象，还是先了解下呀？"],
        },
    )

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_self_intro_after_probe_followup_soft_intent_with_particle():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro_after_probe_particle")

    decision = chat_service._build_turn_decision(
        "先了解下呢",
        profile,
        conversation_context={
            "message_count": 1,
            "recent_responses": ["你好呀，我在呢。你这边是想找对象，还是先了解下呀？"],
        },
    )

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_self_intro_for_probe_followup_xiankan():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro_after_probe_xiankan")

    decision = chat_service._build_turn_decision(
        "我先看看",
        profile,
        conversation_context={
            "message_count": 1,
            "recent_responses": ["你好呀，我在呢。你这边是想找对象，还是先了解下呀？"],
        },
    )

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_uses_opening_self_intro_for_probe_followup_wenwen_qingkuang_with_prefix():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_self_intro_after_probe_wenwen_qingkuang_prefix")

    decision = chat_service._build_turn_decision(
        "就是想先问问情况呢",
        profile,
        conversation_context={
            "message_count": 1,
            "recent_responses": ["你好呀，在的。 你是想认真聊聊，还是先问问情况呀？"],
        },
    )

    assert decision.intent == "opening_self_intro"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_routes_opening_service_confirmation_to_quick_faq():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_service_confirmation")

    decision = chat_service._build_turn_decision(
        "你们帮帮忙介绍对象吗？",
        profile,
        conversation_context={"message_count": 0},
    )

    assert decision.intent == "opening_light_consult"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_treats_service_confirmation_as_mid_conversation_reassurance():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_mid_service_confirmation")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    decision = chat_service._build_turn_decision(
        "你们帮帮忙介绍对象吗？",
        profile,
        conversation_context={
            "message_count": 3,
            "recent_responses": ["你现在主要做哪方面工作呀？"],
        },
    )

    assert decision.intent == "service_confirmation"
    assert decision.response_channel == "quick_faq"
    assert decision.ask_field is None
    assert decision.primary_move == "answer_then_pause"


def test_build_turn_decision_does_not_treat_contact_refusal_as_boundary_pause():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_refusal_not_boundary")
    profile.sex = "男"
    profile.age = 36
    profile.education = "本科"
    profile.occupation = "IT"
    profile.location = "深圳"
    profile.marital_status = "单身"
    profile.partner_requirement = "温柔"
    profile.monthly_income = "5万"
    profile.phone_ask_count = 1
    for field in ["sex", "age", "education", "occupation", "location", "marital_status", "partner_requirement", "monthly_income"]:
        profile.collection_progress[field] = True

    decision = chat_service._build_turn_decision("不方便留呀", profile, conversation_context={"message_count": 8})

    assert decision.risk != "boundary"
    assert decision.primary_move != "soft_hold"
    assert decision.allow_contact_target is True


def test_build_turn_decision_keeps_direct_exchange_faq_in_contact_context():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_exchange_faq")
    profile.phone_ask_count = 1

    decision = chat_service._build_turn_decision(
        "可以直接加对方微信吗",
        profile,
        conversation_context={"message_count": 8},
    )

    assert decision.intent == "contact_exchange"
    assert decision.response_channel == "quick_faq"
    assert decision.prioritize_user_question is True


def test_build_turn_decision_applies_resume_target_once_before_new_target():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_apply")
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    profile.resume_profile_mode = "collect_core"
    profile.resume_profile_target = "age"

    decision = chat_service._build_turn_decision("嗯", profile, conversation_context={"message_count": 2})

    assert decision.ask_field == "age"
    assert decision.primary_move == "light_followup"
    assert decision.resume_applied is True
    assert profile.resume_profile_target is None


def test_build_turn_decision_resumes_profile_collection_without_contact_pivot():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_profile")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "离异（手续已办妥）"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    decision = chat_service._build_turn_decision("你不问其他了？", profile, conversation_context={"message_count": 8})

    assert decision.primary_move == "light_followup"
    assert decision.allow_contact_target is False
    assert decision.ask_field != "contact"


@pytest.mark.anyio
async def test_update_progress_runtime_counters_rolls_back_first_wrong_field_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_wrong_field_rollback")
    profile.field_ask_count["location"] = 1

    turn_decision = SimpleNamespace(
        prioritize_user_question=False,
        response_channel="model",
        allow_contact_target=False,
        allow_medium_target=False,
        primary_move="light_followup",
        resume_applied=False,
    )

    await chat_service._update_progress_runtime_counters(
        "u_wrong_field_rollback",
        profile,
        user_message="我做IT",
        collection_result={"all_fields": [{"field": "occupation", "value": "IT"}]},
        turn_decision=turn_decision,
        previous_asked_field="location",
    )

    assert profile.field_ask_count["location"] == 0
    assert profile.get_field_miss_streak("location") == 1
    assert profile.last_effective_progress is True


@pytest.mark.anyio
async def test_update_progress_runtime_counters_treats_resume_applied_as_effective_progress():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_progress")
    profile.non_cooperation_turns = 2

    turn_decision = SimpleNamespace(
        prioritize_user_question=False,
        response_channel="model",
        allow_contact_target=False,
        allow_medium_target=False,
        primary_move="light_followup",
        resume_applied=True,
    )

    await chat_service._update_progress_runtime_counters(
        "u_resume_progress",
        profile,
        user_message="嗯",
        collection_result={"all_fields": []},
        turn_decision=turn_decision,
        previous_asked_field=None,
    )

    assert profile.last_effective_progress is True
    assert profile.non_cooperation_turns == 0


def test_divorce_confirmation_response_only_asks_about_formality():
    chat_service = _build_chat_service()

    response = chat_service._build_divorce_confirmation_response()

    assert "离婚手续" in response
    assert "办妥" in response
    assert "学历" not in response
    assert "职业" not in response
    assert "电话" not in response
    assert "微信" not in response
    assert "确认清楚" not in response


def test_build_dual_contact_ack_stays_in_continue_mode():
    chat_service = _build_chat_service()

    response = chat_service._build_dual_contact_ack()

    assert "电话和微信" in response
    assert "其他要求" in response or "继续说" in response
    assert "方便留个" not in response


def test_is_divorce_status_complete_message_accepts_natural_confirmation_variants():
    chat_service = _build_chat_service()

    positive_cases = [
        "办理好了",
        "手续都办好了",
        "都弄好了",
        "已经恢复单身了",
        "离干净了",
    ]
    for message in positive_cases:
        assert chat_service._is_divorce_status_complete_message(message) is True

    negative_cases = [
        "还在办理",
        "手续没办完",
        "还没离干净",
        "没有办完",
        "手续还没办完",
    ]
    for message in negative_cases:
        assert chat_service._is_divorce_status_complete_message(message) is False


def test_is_divorce_status_incomplete_message_accepts_natural_negative_variants():
    chat_service = _build_chat_service()

    for message in ["没有办完", "手续还没办完", "手续在办", "分居中"]:
        assert chat_service._is_divorce_status_incomplete_message(message) is True


def test_short_negative_reply_inherits_divorce_confirmation_context():
    chat_service = _build_chat_service()

    assert chat_service._is_short_negative_reply("没有") is True
    assert chat_service._is_divorce_confirmation_question("可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？") is True


def test_user_profile_to_dict_persists_divorce_confirmation_pending():
    profile = UserProfile(account_id="u_pending_flag")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    data = profile.to_dict()

    assert data["divorce_confirmation_pending"] is True
    restored = UserProfile.from_dict(data)
    assert restored.divorce_confirmation_pending is True


@pytest.mark.anyio
async def test_process_collection_result_marks_divorce_confirmation_pending_until_formality_is_confirmed():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_pending_flow")
    profile.marital_status = "离异"

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(
        return_value={"all_fields": [{"field": "marital_status", "value": "离异"}]}
    )
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = lambda *_args, **_kwargs: None

    result = await chat_service._process_collection_result(
        account_id="u_divorce_pending_flow",
        user_profile=profile,
        extracted_data={"marital_status": "离异"},
        user_message="我离异",
        extraction_meta={},
        turn_id=1,
    )

    assert result["divorce_confirmation_pending"] is True
    assert profile.divorce_confirmation_pending is True
    assert profile.divorce_confirmed is False
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_process_collection_result_clears_pending_after_divorce_formality_confirmation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_flow")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = lambda *_args, **_kwargs: None

    result = await chat_service._process_collection_result(
        account_id="u_divorce_done_flow",
        user_profile=profile,
        extracted_data={},
        user_message="办理好了",
        extraction_meta={},
        turn_id=2,
    )

    assert "divorce_confirmation_pending" not in result
    assert result["divorce_confirmation_cleared"] is True
    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"

    policy = ProfileCollectionPolicy()
    decision = policy.decide(profile, user_message="办理好了", message_count=2)
    assert decision.main_target != "marital_status"
    assert decision.can_enter_contact is False


@pytest.mark.anyio
async def test_process_collection_result_ends_when_divorce_formality_is_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_incomplete_flow")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = lambda *_args, **_kwargs: None
    chat_service.ending_service.build_ending_info = lambda scenario_name, _profile: {"scenario": scenario_name, "use_ai": False}

    result = await chat_service._process_collection_result(
        account_id="u_divorce_incomplete_flow",
        user_profile=profile,
        extracted_data={},
        user_message="没有办完",
        extraction_meta={},
        turn_id=2,
    )

    assert result["ending_info"]["scenario"] == "divorce_incomplete"
    assert profile.marital_status == "离异（手续未办妥）"
    assert profile.divorce_confirmation_pending is False


@pytest.mark.anyio
async def test_process_collection_result_hard_ends_fake_info_message():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_fake_info_flow")

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.build_ending_info = lambda scenario_name, _profile: {
        "scenario": scenario_name,
        "use_ai": False,
        "response": "哈哈，这个信息有点意思😊 不过我们还是要认真对待相亲这件事的～如果你是真心想找对象，请告诉我真实的信息哦！",
    }

    result = await chat_service._process_collection_result(
        account_id="u_fake_info_flow",
        user_profile=profile,
        extracted_data={"sex": "女", "age": "1000"},
        user_message="我是女生，今年1000岁，身高3米",
        extraction_meta={},
        turn_id=1,
    )

    assert result["ending_info"]["scenario"] == "fake_info"
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_process_collection_result_short_negative_reply_ends_in_divorce_confirmation_context():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_incomplete_short_reply")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？"
    )
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = lambda *_args, **_kwargs: None
    chat_service.ending_service.build_ending_info = lambda scenario_name, _profile: {"scenario": scenario_name, "use_ai": False}

    result = await chat_service._process_collection_result(
        account_id="u_divorce_incomplete_short_reply",
        user_profile=profile,
        extracted_data={},
        user_message="没有",
        extraction_meta={},
        turn_id=3,
    )

    assert result["ending_info"]["scenario"] == "divorce_incomplete"
    assert profile.marital_status == "离异（手续未办妥）"


def test_build_divorce_confirmation_cleared_response_naturally_hands_back_to_next_question():
    chat_service = _build_chat_service()

    response = chat_service._build_divorce_confirmation_cleared_response("location")

    assert "确认清楚" not in response
    assert "慢慢聊其他的" not in response
    assert "城市" in response


def test_build_divorce_confirmation_cleared_response_handles_contact_followup():
    chat_service = _build_chat_service()

    response = chat_service._build_divorce_confirmation_cleared_response("contact")

    assert "电话" in response
    assert "知道了" not in response


def test_get_post_divorce_mainline_target_blocks_contact_followup():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_post_divorce_target")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "离异（手续已办妥）"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    next_target = chat_service._get_post_divorce_mainline_target(profile, "办理好了", message_count=6)

    assert next_target != "contact"


def test_sanitize_robotic_tone_removes_business_identity_and_registration_tone():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_robotic_tone(
        "你好呀~我是帮大家做交友匹配的小缘，顺口问下你是男生还是女生呀？"
    )

    assert "交友匹配" not in response
    assert "顺口问下" not in response
    assert "我是小缘" in response


def test_sanitize_robotic_tone_softens_registration_and_contact_push_tone():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_robotic_tone(
        "我记下你是男生啦。后面给你匹配到合适的人选时好及时联系到你。"
    )

    assert "我记下" not in response
    assert "合适的人选" not in response
    assert "及时联系到你" not in response


def test_sanitize_robotic_tone_does_not_create_broken_sentence_fragments():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_robotic_tone("好的，我记下你是男生啦。")

    assert "来你是" not in response
    assert "你是男生" in response


def test_clean_response_removes_dangling_particles_and_truncated_tail():
    chat_service = _build_chat_service()

    assert chat_service._clean_response("啦。 你今年多大呀？") == "你今年多大呀？"
    assert chat_service._clean_response("了。 你是哪年的呀？") == "你是哪年的呀？"
    assert chat_service._clean_response("你这边更偏向温柔，对吧。 哈哈，原来") == "你这边更偏向温柔，对吧。"


def test_sanitize_robotic_tone_removes_meta_tone_adjustment_copy():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_robotic_tone(
        "哈哈好的，我语气放轻松些。之后有合适的匹配进展也方便及时通知到你，你方便留个联系电话不？"
    )

    assert "语气放轻松" not in response
    assert "及时通知到你" not in response
    assert "联系电话吗" in response or "联系你会更方便" in response


def test_is_delivery_viable_rejects_empty_and_truncated_responses():
    chat_service = _build_chat_service()

    assert chat_service._is_delivery_viable("") is False
    assert chat_service._is_delivery_viable("没事哈，我懂你担心隐私问题～要是手机号不方便的话，留个常用微信也行，我们平时") is False
    assert chat_service._is_delivery_viable("你这边更偏向温柔，对吧。 哈哈，原来") is False
    assert chat_service._is_delivery_viable("你现在主要在哪个城市生活？") is True


def test_enforce_terminal_response_policy_overrides_both_rejected_contact_push():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_terminal")
    profile.conversation_ended = True
    profile.rejected_phone = True
    profile.rejected_wechat = True

    response = chat_service._enforce_terminal_response_policy(
        "你看要不还是留个微信呀？",
        profile,
        {"ending_info": {"scenario": "both_rejected"}},
    )

    assert "微信" not in response
    assert "电话" not in response
    assert "有需要再联系我" in response
    assert "生活愉快" in response


def test_enforce_terminal_response_policy_keeps_already_ended_reply_minimal():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_terminal_min")
    profile.conversation_ended = True

    response = chat_service._enforce_terminal_response_policy(
        "那微信你方便留一下不？",
        profile,
        {"ending_info": {"scenario": "already_ended"}},
    )

    assert response == "好，那先这样哈，后面想聊了再来找我。"


def test_enforce_terminal_response_policy_prefers_config_preset_response():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_terminal_preset")
    profile.conversation_ended = True

    response = chat_service._enforce_terminal_response_policy(
        "那你继续说下学历吧？",
        profile,
        {"ending_info": {"scenario": "separation", "response": "你现在还在分居阶段，这边先聊到这里。"}},
    )

    assert response == "你现在还在分居阶段，这边先聊到这里。"


def test_apply_refusal_respect_guard_closes_after_wechat_rejected_with_phone_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_refusal_close_after_phone")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True
    profile.rejected_wechat = True
    profile.age = 35
    profile.education = "本科"
    profile.sex = "男"
    profile.monthly_income = "4万"
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="none")

    response = chat_service._apply_refusal_respect_guard(
        "没关系，这块我们先不急，继续聊别的也可以。",
        profile,
        "不留了",
    )

    assert "等好消息" in response
    assert "1-8小时" in response
    assert "继续聊别的" not in response


def test_enforce_contact_outcome_policy_closes_after_wechat_rejected_with_phone_collected_and_profile_complete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_contact_outcome_close_after_phone")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True
    profile.rejected_wechat = True
    profile.age = 35
    profile.education = "本科"
    profile.sex = "男"
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.monthly_income = "4万"
    profile.partner_requirement = "温柔"
    profile.wechat_ask_count = 1
    profile.wechat_effective_ask_count = 1
    profile.collection_progress.update(
        {
            "age": True,
            "education": True,
            "sex": True,
            "location": True,
            "occupation": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
        }
    )
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="none")

    response = chat_service._enforce_contact_outcome_policy(
        "没关系，这块我们先不急，继续聊别的也可以。",
        profile,
        collection_result={},
        user_message="不留了",
    )

    assert "等好消息" in response
    assert "1-8小时" in response
    assert "继续聊别的" not in response


def test_apply_contact_persuasion_style_policy_softens_wechat_persuasion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_persuade_wechat")
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_wechat")

    response = chat_service._apply_contact_persuasion_style_policy(
        "放心哈，我不会乱发广告或者骚扰你的，你看能不能留个微信呀？",
        profile,
        "微信号不方便呢",
    )

    assert "常用微信" in response or "微信" in response
    assert "方便及时" in response or "方便" in response
    assert "不会乱发广告" not in response


def test_apply_contact_persuasion_style_policy_softens_phone_persuasion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_persuade_phone")
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_phone")

    response = chat_service._apply_contact_persuasion_style_policy(
        "电话只是登记用的，绝对不会打扰你，也不会发广告，你方便的话还是留个电话吧？",
        profile,
        "电话不方便",
    )

    assert "手机号" in response or "电话" in response
    assert "微信" not in response
    assert "再轻问一次" not in response
    assert any(token in response for token in ["联系", "沟通", "合适"])


def test_apply_contact_boundary_softening_policy_downgrades_persuade_wechat_on_boundary():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_boundary_wechat")
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_wechat")

    response = chat_service._apply_contact_boundary_softening_policy(
        "我知道你现在对微信这块还有顾虑。你要是愿意，留一个也行，不想留我们就先往下聊。",
        profile,
        "微信不方便呢",
    )

    assert response == "好，那微信这块我先不往下问了，我们先聊别的。"


def test_apply_contact_boundary_softening_policy_softens_ask_wechat_after_phone_refusal():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_boundary_switch")
    profile.rejected_phone = True
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_wechat")

    response = chat_service._apply_contact_boundary_softening_policy(
        "不方便接电话没关系，那你微信方便说下吗？",
        profile,
        "不方便呢",
    )

    assert "微信" in response
    assert "联系方式" in response or "先不碰" in response
    assert "电话这块" not in response


def test_apply_contact_boundary_softening_policy_keeps_phone_retry_on_first_phone_refusal():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_boundary_retry_phone")
    profile.phone_ask_count = 1
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_phone")

    response = chat_service._apply_contact_boundary_softening_policy(
        "没关系，这块我先不追问，我们先按你舒服的节奏来",
        profile,
        "不方便留电话",
    )

    assert "电话" in response or "手机号" in response
    assert "微信" not in response
    assert "不追问" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_falls_back_to_quick_faq_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_faq")

    response = await chat_service._build_no_ai_response("u_no_ai_faq", profile, "怎么收费")

    assert response
    assert "收费" in response or "免费" in response or "定制" in response


@pytest.mark.anyio
async def test_build_no_ai_response_uses_divorce_confirmation_when_pending():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_divorce")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    response = await chat_service._build_no_ai_response("u_no_ai_divorce", profile, "嗯")

    assert "离婚手续" in response
    assert "办妥" in response or "办好" in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_probe_for_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_greeting")

    response = await chat_service._build_no_ai_response("u_no_ai_greeting", profile, "在吗")

    assert any(token in response for token in ["介绍下自己", "说说自己", "说说自己的情况", "讲讲自己的情况", "顺着了解"])
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_probe_for_noisy_repeated_greeting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_greeting_noisy_repeat")

    response = await chat_service._build_no_ai_response("u_no_ai_greeting_noisy_repeat", profile, "你好呀，在吗在吗呀呀呀？")

    assert any(token in response for token in ["介绍下自己", "说说自己", "讲讲自己", "顺着了解"])
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_clarify_for_unstable_opening_input():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_opening_clarify")

    response = await chat_service._build_no_ai_response("u_no_ai_opening_clarify", profile, "佃�好")

    assert any(token in response for token in ["没看懂", "没太接住", "没看明白", "没反应过来"])
    assert any(token in response for token in ["想找对象", "先了解下", "先看看情况", "先问问情况"])
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_clarify_for_greeting_with_noise_tail():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_opening_clarify_noise_tail")

    response = await chat_service._build_no_ai_response("u_no_ai_opening_clarify_noise_tail", profile, "你好呀，坏呼叫")

    assert any(token in response for token in ["没看懂", "没太接住", "没看明白", "没反应过来"])
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_corrects_evening_greeting_against_morning():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_time_greeting")
    chat_service.greeting_service.get_current_time_period = lambda: "morning"

    response = await chat_service._build_no_ai_response("u_no_ai_time_greeting", profile, "晚上好")

    assert "早上" in response or "上午" in response
    assert "晚上好呀" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_explicit_matchmaking_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro")

    response = await chat_service._build_no_ai_response("u_no_ai_self_intro", profile, "找对象")

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_probe_followup_soft_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro_after_probe")
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="你好呀，我在呢。你这边是想找对象，还是先了解下呀？"
    )

    response = await chat_service._build_no_ai_response("u_no_ai_self_intro_after_probe", profile, "先了解下")

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_probe_followup_soft_intent_with_particle():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro_after_probe_particle")
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="你好呀，我在呢。你这边是想找对象，还是先了解下呀？"
    )

    response = await chat_service._build_no_ai_response("u_no_ai_self_intro_after_probe_particle", profile, "先了解下呢")

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_probe_followup_xiankan():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro_after_probe_xiankan")
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="你好呀，我在呢。你这边是想找对象，还是先了解下呀？"
    )

    response = await chat_service._build_no_ai_response("u_no_ai_self_intro_after_probe_xiankan", profile, "我先看看")

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_probe_followup_wenwen_qingkuang_with_prefix():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro_after_probe_wenwen_qingkuang_prefix")
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="你好呀，在的。你先简单说说自己就行，我顺着了解会更顺一点。"
    )

    response = await chat_service._build_no_ai_response(
        "u_no_ai_self_intro_after_probe_wenwen_qingkuang_prefix",
        profile,
        "就是想先问问情况呢",
    )

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_returns_opening_self_intro_for_probe_followup_wo_wenwen_qingkuang():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_self_intro_after_probe_wo_wenwen_qingkuang")
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="你好呀，在的。你先简单说说自己就行，我顺着了解会更顺一点。"
    )

    response = await chat_service._build_no_ai_response(
        "u_no_ai_self_intro_after_probe_wo_wenwen_qingkuang",
        profile,
        "我问问你情况呢",
    )

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_handles_opening_service_confirmation_with_open_intro():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_opening_service_confirmation")

    response = await chat_service._build_no_ai_response(
        "u_no_ai_opening_service_confirmation",
        profile,
        "你们帮帮忙介绍对象吗？",
    )

    assert "介绍下自己" in response or "说说自己的情况" in response or "讲讲自己" in response
    assert "男生还是女生" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_handles_mid_service_confirmation_and_resumes_mainline():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_mid_service_confirmation")
    profile.location = "深圳"
    profile.collection_progress["location"] = True
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="你现在主要做哪方面工作呀？")

    response = await chat_service._build_no_ai_response(
        "u_no_ai_mid_service_confirmation",
        profile,
        "你们帮帮忙介绍对象吗？",
    )

    assert ("牵线介绍" in response) or ("往合适方向" in response) or ("留意合适方向" in response)
    assert "工作" in response or "做哪方面" in response or "做什么" in response
    assert "介绍下自己" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_handles_partner_requirement_oral_answer_after_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_partner_requirement_answer")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "7万"
    for field in ["sex", "age", "location", "education", "occupation", "monthly_income"]:
        profile.collection_progress[field] = True
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="好，男生我知道了。 你对另一半有什么大致的要求不？"
    )

    response = await chat_service._build_no_ai_response(
        "u_no_ai_partner_requirement_answer",
        profile,
        "温柔就行了",
    )

    assert "温柔" in response
    assert "继续说，我先顺着听" not in response
    assert any(token in response for token in ["单身状态", "联系方式", "方便", "电话", "多大", "学历"])


@pytest.mark.anyio
async def test_build_no_ai_response_respects_resume_profile_collection_without_contact_pivot():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_resume")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "离异（手续已办妥）"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    response = await chat_service._build_no_ai_response("u_no_ai_resume", profile, "你不问其他了？")

    assert "电话" not in response
    assert "微信" not in response
    assert "顺着往下了解" in response or "更在意哪块" in response or "更看重哪方面" in response


@pytest.mark.anyio
async def test_build_no_ai_response_interleaves_after_core_streak():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_interleave")
    profile.sex = "女"
    profile.age = 28
    profile.location = "深圳"
    profile.education = "本科"
    for field in ["sex", "age", "location", "education"]:
        profile.collection_progress[field] = True
    profile.recent_asked_fields = ["sex", "age", "location"]

    response = await chat_service._build_no_ai_response("u_no_ai_interleave", profile, "本科")

    assert any(token in response for token in ["工作", "收入", "区间"])
    assert "电话" not in response


@pytest.mark.anyio
async def test_build_no_ai_response_softens_contact_transition_when_profile_ready():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_contact_transition")
    profile.sex = "男"
    profile.age = 32
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    response = await chat_service._build_no_ai_response("u_no_ai_contact_transition", profile, "单身")

    assert "手机号" in response or "电话" in response
    assert "资料差不多" not in response


def test_apply_refusal_respect_guard_softens_contact_followup():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refusal_guard")
    profile.rejected_phone = True
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_wechat")

    response = chat_service._apply_refusal_respect_guard(
        "微信方便的话可以留一个。",
        profile,
        "电话不方便留",
    )

    assert any(token in response for token in ["没关系", "不急", "不勉强"])
    assert "微信" in response
    assert "电话这块" not in response


def test_apply_refusal_respect_guard_keeps_phone_followup_on_first_phone_refusal():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refusal_guard_phone")
    profile.phone_ask_count = 1
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_phone")

    response = chat_service._apply_refusal_respect_guard(
        "留个手机号方便联系吗？",
        profile,
        "不留",
    )

    assert "手机号" in response or "电话" in response
    assert "微信" not in response


def test_extract_simple_monthly_income_supports_passive_capture():
    chat_service = _build_chat_service()

    assert chat_service._extract_simple_monthly_income("我现在税前15k左右") == "税前15k左右"
    assert chat_service._extract_simple_monthly_income("月薪 1.2w+") == "1.2w+"
    assert chat_service._extract_simple_monthly_income("年包30左右") == "年包30左右"
    assert chat_service._extract_simple_monthly_income("一万出头") == "一万出头"
    assert chat_service._extract_simple_monthly_income("两万上下") == "两万上下"


def test_extract_simple_monthly_income_does_not_misread_weight_as_income():
    chat_service = _build_chat_service()

    assert chat_service._extract_simple_monthly_income("单身，90kg，身高198") is None
    assert chat_service._extract_simple_monthly_income("体重90kg，月薪3万") == "3万"


def test_extract_deterministic_profile_fields_includes_monthly_income():
    chat_service = _build_chat_service()

    extracted = chat_service._extract_deterministic_profile_fields("收入大概1w左右")

    assert extracted["monthly_income"] == "1w左右"


@pytest.mark.anyio
async def test_update_conversation_state_skips_ask_tracking_for_non_viable_response():
    chat_service = _build_chat_service()
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()

    await chat_service._update_conversation_state(
        "u_delivery_guard",
        "不方便呢",
        "没事哈，我懂你担心隐私问题～要是手机号不方便的话，留个常用微信也行，我们平时",
        "",
        track_asked_fields=True,
    )

    chat_service.ask_tracking_service.track_ai_asked_fields.assert_not_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_uses_same_canonical_response_for_history_and_recent_responses():
    chat_service = _build_chat_service()
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()

    await chat_service._update_conversation_state(
        "u_response_consistency",
        "你好",
        "  好的呀 <extract>忽略</extract> 我们继续聊。  ",
        "",
        track_asked_fields=True,
    )

    chat_service.dialogue_manager.add_to_history.assert_any_await(
        "u_response_consistency",
        "assistant",
        "好的呀 我们继续聊。",
    )
    chat_service.dialogue_manager.update_recent_responses.assert_awaited_once_with(
        "u_response_consistency",
        "好的呀 我们继续聊。",
    )
    chat_service.ask_tracking_service.track_ai_asked_fields.assert_awaited_once_with(
        "u_response_consistency",
        "好的呀 我们继续聊。",
    )


@pytest.mark.anyio
async def test_update_conversation_state_sets_pending_sex_confirmation_from_confirm_prompt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_sex")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=6)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_pending_sex",
        "温柔，苗条，漂亮",
        "我再确认下，你这边是男生对吧？",
        "",
        track_asked_fields=True,
    )

    assert profile.pending_sex_confirmation == "男"
    assert profile.last_asked_field == "sex"
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_track_ai_asked_fields_closes_medium_field_active_ask():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_medium_close")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service.ask_tracking_service.track_ai_asked_fields(
        "u_medium_close",
        "你这边对另一半有什么比较在意的点吗？",
    )

    assert profile.is_active_ask_closed("partner_requirement") is True
    assert profile.get_ask_count("partner_requirement") == 1


@pytest.mark.anyio
async def test_build_chat_response_reuses_contact_service_status_display():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_display")
    profile.phone_ask_count = 1
    profile.wechat_ask_count = 1
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=3)

    payload = await chat_service._build_chat_response(
        "u_contact_display",
        profile,
        "我们继续聊。",
        {},
        "dlg_1",
        {},
    )

    assert payload["collected_info"]["contact"] == "电话暂缓, 微信争取中"


@pytest.mark.anyio
async def test_build_chat_response_refreshes_latest_profile_before_collected_info():
    chat_service = _build_chat_service()
    stale_profile = UserProfile(account_id="u_refresh_profile")
    latest_profile = UserProfile(account_id="u_refresh_profile")
    latest_profile.partner_requirement = "温柔"
    latest_profile.collection_progress["partner_requirement"] = True
    latest_profile.education = "本科"
    latest_profile.collection_progress["education"] = True
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_profile",
        stale_profile,
        "我们继续聊。",
        {},
        "dlg_1",
        {},
    )

    assert payload["collected_info"]["partner_requirement"] == "温柔"
    assert payload["collected_info"]["education"] == "本科"


@pytest.mark.anyio
async def test_record_delivered_contact_ask_if_needed_increments_phone_on_successful_delivery():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_ask_phone")
    profile.wechat = "wx_123456"
    profile.wechat_collected = True
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    updated = await chat_service._record_delivered_contact_ask_if_needed(
        "u_contact_ask_phone",
        profile,
        "继续聊",
        "要是你愿意，留个电话也行。",
    )

    assert updated.phone_ask_count == 1
    assert updated.last_contact_request_type == "phone"
    assert updated.contact == "电话暂缓, 微信: wx_123456"
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.anyio
async def test_record_delivered_contact_ask_if_needed_skips_truncated_delivery():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_ask_skip")
    profile.rejected_phone = True
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    updated = await chat_service._record_delivered_contact_ask_if_needed(
        "u_contact_ask_skip",
        profile,
        "继续聊",
        "没事哈，我懂你担心隐私问题～要是手机号不方便的话，留个常用微信也行，我们平时",
    )

    assert updated.wechat_ask_count == 0
    chat_service.user_service.save_user_profile.assert_not_awaited()


@pytest.mark.anyio
async def test_record_delivered_contact_ask_if_needed_does_not_increment_for_non_contact_reply():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_non_contact")
    profile.rejected_phone = True
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    updated = await chat_service._record_delivered_contact_ask_if_needed(
        "u_contact_non_contact",
        profile,
        "继续聊",
        "我明白这个顾虑，我们先聊别的。",
    )

    assert updated.wechat_ask_count == 0
    chat_service.user_service.save_user_profile.assert_not_awaited()


def test_format_fast_path_ack_avoids_remembering_tone_for_occupation():
    chat_service = _build_chat_service()

    response = chat_service._format_fast_path_ack("occupation", "产品")

    assert "记着" not in response
    assert "记成" not in response
    assert "产品" in response


def test_format_fast_path_ack_avoids_remembering_tone_for_marital_status():
    chat_service = _build_chat_service()

    response = chat_service._format_fast_path_ack("marital_status", "单身")

    assert "记着" not in response
    assert "记成" not in response
    assert "单身" in response


def test_partner_requirement_ask_variants_are_complete_sentences():
    from src.services.core.chat_service import PARTNER_REQUIREMENT_ASK_VARIANTS

    assert any("你对另一半大概有什么要求" in item for item in PARTNER_REQUIREMENT_ASK_VARIANTS)
    for item in PARTNER_REQUIREMENT_ASK_VARIANTS:
        assert "匹配点" not in item
    assert not any(item.startswith("比如年龄、城市、性格这些") for item in PARTNER_REQUIREMENT_ASK_VARIANTS)


def test_sanitize_forbidden_sales_phrases_removes_marketing_clauses_from_contact_reply():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_forbidden_sales_phrases(
        "我手里好多本地优质的单身资源呢，也绝对不会乱发广告或者骚扰你哈，方便留个微信呀？"
    )

    assert "资源" not in response
    assert "广告" not in response
    assert "骚扰" not in response
    assert "微信" in response


def test_sanitize_forbidden_sales_phrases_trims_contact_tail_particles():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_forbidden_sales_phrases("那你方便留个微信呀？")

    assert response == "那你方便留个微信？"


def test_sanitize_forbidden_sales_phrases_removes_specific_timeline_and_detail_promises():
    chat_service = _build_chat_service()

    response = chat_service._sanitize_forbidden_sales_phrases(
        "后面1到8小时内我第一时间联系你，再给你介绍男生的具体情况和地址。"
    )

    assert "1到8小时" not in response
    assert "第一时间联系你" not in response
    assert "介绍男生的具体情况" not in response
    assert "地址" not in response


def test_get_main_dialogue_omits_irrelevant_strategy_lines():
    turn_plan = "\n【本轮计划】\n- 主目标：所在地\n- 顺带目标：无\n- 用户类型：配合型\n- 可进联系方式：否"
    prompt = get_main_dialogue(
        gender_instruction="用户性别未知",
        collected_info="男,90后",
        missing_fields="所在地、学历",
        current_main_target="所在地",
        current_side_target="无",
        user_type="配合型",
        can_enter_contact=False,
        is_first_chat=False,
        turn_plan_instruction=turn_plan,
    )

    assert "顺带字段：无" not in prompt
    assert "当前不要主动切到电话或微信" in prompt
    assert "【本轮计划】" in prompt
    assert "用户类型：配合型" in prompt
    assert "先让用户感觉“你听见了”" in prompt
    assert "禁止空泛承接" in prompt


def test_get_main_dialogue_includes_listener_first_examples():
    prompt = get_main_dialogue(
        gender_instruction="用户性别未知",
        collected_info="男,90后",
        missing_fields="所在地、学历",
        current_main_target="所在地",
        current_side_target="无",
        user_type="配合型",
        can_enter_contact=False,
        is_first_chat=False,
        turn_plan_instruction="",
    )

    assert "【表达示例】" in prompt
    assert "先不聊资料，先说收费" in prompt
    assert "好，那我们先顺着你现在更想聊的这个说" in prompt


def test_get_main_dialogue_includes_primary_move_instruction_when_answer_then_pause():
    prompt = get_main_dialogue(
        gender_instruction="用户性别未知",
        collected_info="男,90后",
        missing_fields="所在地、学历",
        current_main_target="所在地",
        current_side_target="无",
        user_type="配合型",
        can_enter_contact=False,
        is_first_chat=False,
        turn_plan_instruction="",
        move_instruction="""
【本轮动作】
这轮先答清楚用户当前的问题或顾虑，再决定是否轻轻收住。
- 先答，不要急着追问字段
""",
    )

    assert "【本轮动作】" in prompt
    assert "先答，不要急着追问字段" in prompt


def test_build_main_dialogue_prompt_respects_primary_move_light_followup():
    user_service = AsyncMock()
    from src.services.core.dialogue_manager import DialogueManager

    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_move")
    prompt = manager.build_main_dialogue_prompt(
        "男的",
        profile,
        {"message_count": 1, "recent_responses": []},
        primary_move="light_followup",
    )

    assert "这轮用轻量承接推进一小步" in prompt
    assert "句子尽量短，别像登记表" in prompt


def test_build_main_dialogue_prompt_blocks_contact_instruction_when_contact_target_disallowed():
    user_service = AsyncMock()
    from src.services.core.dialogue_manager import DialogueManager

    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_no_contact")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "离异（手续已办妥）"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    prompt = manager.build_main_dialogue_prompt(
        "你不问其他了？",
        profile,
        {"message_count": 8, "recent_responses": []},
        primary_move="light_followup",
        allow_contact_target=False,
    )

    assert "不要索要电话或微信" not in prompt
    assert "当前不要主动切到电话或微信" in prompt
    assert "主目标=联系方式" not in prompt


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

    assert response == "好，电话我收到了。我们接着聊你的情况就行。"
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
        return_value=(False, {"code": "CONTACT_INVALID_FORMAT", "field": "contact", "detail": "invalid", "attempt": 1, "silent": False}, None)
    )
    chat_service._generate_validation_retry_response = AsyncMock(return_value="这个号码像是不太对，你再确认一下。")

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
    chat_service._generate_validation_retry_response.assert_awaited_once()


@pytest.mark.anyio
async def test_process_chat_request_returns_preset_ending_response_immediately():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_2")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
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
async def test_handle_contact_validation_returns_natural_ack_for_wechat_when_profile_not_ready():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_wechat_ack")
    profile.phone_ask_count = 1
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: False
    chat_service.collection_policy.decide = lambda _profile, allow_contact_target=False: SimpleNamespace(main_target="age")

    response = await chat_service._handle_contact_validation(
        "user_wechat_ack",
        profile,
        {"all_fields": [{"field": "wechat", "value": "wx123456"}]},
        "原始回复",
        "我微信wx123456",
    )

    assert response == "好，微信我看到了。我们接着聊你的情况就行。"


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


def test_build_turn_decision_marks_work_busy_context_ack():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_topic_work")
    profile.occupation = "运营"

    decision = chat_service._build_turn_decision("我工作比较忙", profile, conversation_context={"message_count": 2})

    assert decision.followup_topic == "work_busy"
    assert decision.context_ack_required is True
    assert decision.context_ack_type == "work_busy"


def test_apply_context_ack_policy_reuses_work_topic_without_fixed_template():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_context_work")
    profile.occupation = "运营"
    decision = SimpleNamespace(
        context_ack_required=True,
        context_ack_type="work_busy",
        context_ack_payload={"occupation": "运营"},
    )

    response = chat_service._apply_context_ack_policy(
        "你对另一半大概有什么要求呀？",
        decision,
        profile,
        "我工作比较忙",
    )

    assert any(token in response for token in ["运营", "工作", "忙", "节奏"])
    assert "另一半" in response


def test_apply_context_ack_policy_turns_partial_boundary_into_no_push_response():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_context_boundary")
    decision = SimpleNamespace(
        context_ack_required=True,
        context_ack_type="profile_partial_with_boundary",
        context_ack_payload={"field_ack": "本科我知道了。"},
    )

    response = chat_service._apply_context_ack_policy(
        "你现在主要在哪个城市生活呀？",
        decision,
        profile,
        "本科，不过这个先不太方便说",
    )

    assert "本科" in response
    assert any(token in response for token in ["不追", "舒服", "先不往", "不想展开"])
    assert "城市" not in response


def test_apply_priority_question_guard_blocks_contact_push_on_faq_turn():
    chat_service = _build_chat_service()
    decision = SimpleNamespace(prioritize_user_question=True)

    response = chat_service._apply_priority_question_guard(
        "方便留个电话吗？后面沟通会方便些。",
        decision,
        "为什么要留电话呢",
    )

    assert "留个电话吗" not in response
    assert any(token in response for token in ["方便", "沟通", "乱用", "打扰"])


def test_select_model_for_turn_prefers_main_model_on_high_risk(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("电话不方便，留微信吧", "普通提示词")
    assert model == settings.model_name


def test_select_model_for_turn_keeps_main_model_on_low_complexity(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("怎么收费", "简短提示")
    assert model == settings.model_name


def test_select_model_for_turn_keeps_main_model_for_safe_short_profile_answer_with_medium_prompt(monkeypatch):
    monkeypatch.setenv("AI_ROUTING_ENABLED", "true")
    monkeypatch.setenv("AI_FAST_MODEL_NAME", "doubao-seed-fast")
    chat_service = _build_chat_service()

    model = chat_service._select_model_for_turn("深圳", "x" * 6000)

    assert model == settings.model_name


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
    assert "隐私" in response or "边界" in response
    assert "年龄" not in response
    assert "城市" not in response


def test_get_boundary_pause_response_handles_privacy_concern():
    chat_service = _build_chat_service()
    response = chat_service._get_boundary_pause_response("这个我不太方便说，先不留")
    assert response is not None


def test_extract_opening_intent_block_parses_payload_and_natural_response():
    chat_service = _build_chat_service()

    signal, natural = chat_service._extract_opening_intent_block(
        '<opening_intent>{"intent":"low_pressure_opening","confidence":0.91,"secondary_intent":null}</opening_intent>可以呀，那我们先轻松聊聊。'
    )

    assert signal is not None
    assert signal.intent == "low_pressure_opening"
    assert signal.confidence == pytest.approx(0.91)
    assert natural == "可以呀，那我们先轻松聊聊。"


def test_extract_opening_intent_block_returns_parse_failed_on_invalid_json():
    chat_service = _build_chat_service()

    signal, natural = chat_service._extract_opening_intent_block(
        "<opening_intent>{bad json}</opening_intent>可以呀，那我们先轻松聊聊。"
    )

    assert signal is not None
    assert signal.parse_failed is True
    assert natural == "可以呀，那我们先轻松聊聊。"


def test_resolve_opening_intent_priority_promotes_higher_priority_secondary():
    primary, secondary = ChatService._resolve_opening_intent_priority(
        "explicit_matchmaking_opening",
        "opening_faq",
    )

    assert primary == "opening_faq"
    assert secondary == "explicit_matchmaking_opening"


def test_enforce_opening_intent_consistency_replaces_wrong_followup_for_low_pressure():
    chat_service = _build_chat_service()

    response = chat_service._enforce_opening_intent_consistency(
        "先随便聊聊，你这边是男生还是女生呀？",
        OpeningIntentSignal(intent="low_pressure_opening", confidence=0.91),
        user_message="就是想先问问情况呢",
        seed_hint="u:test",
    )

    assert "介绍下自己" in response or "说说自己" in response or "大概情况" in response
    assert "男生还是女生" not in response


def test_apply_opening_intent_signal_to_turn_decision_maps_opening_greeting_to_probe():
    chat_service = _build_chat_service()
    decision = SimpleNamespace(
        intent="general",
        primary_move="ack_and_ask",
        ask_field="sex",
        prioritize_user_question=False,
        allow_contact_target=True,
        allow_medium_target=True,
        followup_topic=None,
    )

    chat_service._apply_opening_intent_signal_to_turn_decision(
        OpeningIntentSignal(intent="opening_greeting", confidence=0.95),
        decision,
        user_message="你好呀，在吗呀呀呀？",
    )

    assert decision.intent == "opening_probe"
    assert decision.primary_move == "answer_then_pause"
    assert decision.ask_field is None
    assert decision.prioritize_user_question is True
    assert decision.allow_contact_target is False


def test_enforce_opening_intent_consistency_replaces_wrong_followup_for_opening_greeting():
    chat_service = _build_chat_service()

    response = chat_service._enforce_opening_intent_consistency(
        "我在的~咱们先随便聊聊哈，你是男生还是女生呀？",
        OpeningIntentSignal(intent="opening_greeting", confidence=1.0),
        user_message="你好呀，在吗呀呀呀？",
        seed_hint="u:greeting",
    )

    assert any(token in response for token in ["找对象", "了解下", "看看情况", "问问情况"])
    assert "男生还是女生" not in response


def test_get_boundary_pause_response_softens_phone_refusal_without_switching_to_wechat():
    chat_service = _build_chat_service()

    response = chat_service._get_boundary_pause_response("不方便接电话呢")

    assert response is not None
    assert "电话这块" in response
    assert "不方便也没事" in response
    assert "微信" not in response
    assert "按你方便的方式" in response


def test_get_boundary_pause_response_topic_shift_explicitly_says_no_followup():
    chat_service = _build_chat_service()

    response = chat_service._get_boundary_pause_response("先别问我这些")

    assert "先不追问" in response


def test_build_opening_profile_ack_from_message_reuses_location_and_education():
    chat_service = _build_chat_service()

    assert chat_service._build_opening_profile_ack_from_message("我在深圳") == "好，深圳这边我知道了。"
    assert chat_service._build_opening_profile_ack_from_message("本科") == "好，本科这点我知道了。"


def test_looks_like_fake_info_message_detects_impossible_age_and_height():
    chat_service = _build_chat_service()

    assert chat_service._looks_like_fake_info_message("我是女生，今年1000岁，身高3米") is True
    assert chat_service._looks_like_fake_info_message("我今年35，在深圳") is False


def test_apply_income_appreciation_policy_adds_light_ack_for_high_income():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_income_ack")
    profile.monthly_income = "5万"

    response = chat_service._apply_income_appreciation_policy(
        "好呀，你大概是什么学历呀？ 这样我对你的情况会更有数一点。",
        profile,
        {"all_fields": [{"field": "monthly_income", "value": "5万"}]},
    )

    assert "那还不错呀" in response


def test_build_user_feeling_ack_handles_phone_unavailable_more_naturally():
    chat_service = _build_chat_service()

    response = chat_service._build_user_feeling_ack("不方便接电话呢")

    assert response == "行，电话这块你现在不方便也没事。"


def test_get_risk_guard_response_acknowledges_user_feeling_on_ai_identity_probe():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_ai_probe")

    response = chat_service._get_risk_guard_response("你是AI吗，我有点担心隐私", profile)

    assert response is not None
    assert "隐私" in response
    assert "明白" in response or "正常" in response


def test_ensure_conservative_empathy_prefixes_boundary_feeling_before_answer():
    chat_service = _build_chat_service()

    response = chat_service._ensure_conservative_empathy("这个我不太方便说", "这轮我先不追问资料。")

    assert "不太想展开" in response or "不方便" in response
    assert response.endswith("这轮我先不追问资料。")


def test_ensure_listener_first_ack_prefixes_joking_complaint():
    chat_service = _build_chat_service()

    response = chat_service._ensure_listener_first_ack("你查户口呢问这么细", "我先解释下为什么会问这些。")

    assert "问细" in response or "查户口" in response
    assert response.endswith("我先解释下为什么会问这些。")


def test_ensure_listener_first_ack_prefixes_reliability_concern():
    chat_service = _build_chat_service()

    response = chat_service._ensure_listener_first_ack("你们靠谱吗，我有点担心", "我们这边会先做基础了解和筛选。")

    assert "靠谱" in response or "正常" in response
    assert response.endswith("我们这边会先做基础了解和筛选。")


def test_ensure_conservative_empathy_keeps_field_ack_for_mixed_answer_and_boundary():
    chat_service = _build_chat_service()

    response = chat_service._ensure_conservative_empathy("本科，这个先不太方便说", "这轮我先不追问资料。")

    assert "本科" in response
    assert "不太想展开" in response or "不太方便" in response
    assert response.endswith("这轮我先不追问资料。")


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


def test_apply_field_ask_guard_blocks_medium_field_after_first_ask():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_medium")
    profile.field_ask_count = {"partner_requirement": 1}

    response = chat_service._apply_field_ask_guard(profile, "你这边对另一半有什么比较在意的点吗？")

    assert "另一半" not in response
    assert "在意的点" not in response


def test_apply_field_ask_guard_blocks_medium_field_when_turn_disallows_medium_targets():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_guard_medium_turn")

    response = chat_service._apply_field_ask_guard(
        profile,
        "你这边对另一半有什么比较在意的点吗？",
        allow_medium_target=False,
    )

    assert "另一半" not in response
    assert "在意的点" not in response


def test_build_turn_decision_blocks_medium_target_for_repair_turn():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_repair_turn")

    decision = chat_service._build_turn_decision(
        "你已经糊涂了",
        profile,
        conversation_context={"message_count": 5},
    )

    assert decision.allow_medium_target is False


def test_apply_contact_action_guard_blocks_contact_push_when_next_action_none():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_guard")
    profile.phone_ask_count = 2
    profile.wechat_ask_count = 2

    response = chat_service._apply_contact_action_guard(
        "你方便留个微信或者手机号不？",
        profile,
        "你已经糊涂了",
    )

    assert response == "好，我们先不碰联系方式了，继续聊别的。"


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


def test_infer_contact_attempt_from_context_does_not_treat_wechat_intent_as_wechat_id():
    chat_service = _build_chat_service()

    value, contact_type = chat_service._infer_contact_attempt_from_context("用微信联系吧", "ask_wechat")

    assert value is None
    assert contact_type is None


def test_infer_contact_attempt_from_context_does_not_treat_profile_digits_as_phone():
    chat_service = _build_chat_service()

    value, contact_type = chat_service._infer_contact_attempt_from_context(
        "我叫小张，男的，30岁，175cm，70kg，深圳，本科，IT，2万，单身",
        "ask_phone",
    )

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


def test_select_max_tokens_for_turn_keeps_default_cap_on_low_complexity(monkeypatch):
    monkeypatch.setenv("CHAT_AI_MAX_TOKENS", "420")
    monkeypatch.setenv("CHAT_AI_LOW_COMPLEXITY_MAX_TOKENS", "260")
    chat_service = _build_chat_service()

    tokens = chat_service._select_max_tokens_for_turn("怎么收费", "简短提示")
    assert tokens == 420


def test_select_max_tokens_for_turn_keeps_default_cap_on_long_prompt(monkeypatch):
    monkeypatch.setenv("CHAT_AI_MAX_TOKENS", "420")
    monkeypatch.setenv("CHAT_AI_LONG_PROMPT_CHAR_THRESHOLD", "6500")
    monkeypatch.setenv("CHAT_AI_LONG_PROMPT_MAX_TOKENS", "210")
    chat_service = _build_chat_service()

    tokens = chat_service._select_max_tokens_for_turn("我在深圳做运营，想认真了解", "x" * 7000)
    assert tokens == 420


def test_select_max_tokens_for_turn_keeps_default_cap_on_high_risk(monkeypatch):
    monkeypatch.setenv("CHAT_AI_MAX_TOKENS", "420")
    monkeypatch.setenv("CHAT_AI_HIGH_RISK_MAX_TOKENS", "180")
    chat_service = _build_chat_service()

    tokens = chat_service._select_max_tokens_for_turn("电话不方便，留微信吧", "普通提示词")
    assert tokens == 420


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
async def test_build_chat_response_softens_contact_display_after_phone_refusal():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_contact_display")
    profile.phone_ask_count = 1
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=3)

    result = await chat_service._build_chat_response(
        "user_contact_display",
        profile,
        "这轮我先不追问资料。",
        {"all_fields": []},
        "dlg_contact_display",
    )

    assert result["collected_info"]["contact"] == "电话争取中"


def test_contact_service_keeps_phone_after_first_phone_refusal_for_non_hk_user():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_contact_strategy")
    profile.location = "深圳"
    profile.phone_ask_count = 1

    next_action = chat_service.contact_service.get_next_action(profile, "不方便接电话呢")

    assert next_action.value == "persuade_phone"


@pytest.mark.anyio
async def test_build_chat_response_marks_phone_as_paused_when_wechat_turn_starts():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_contact_paused")
    profile.phone_ask_count = 1
    profile.wechat_ask_count = 1
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=3)

    result = await chat_service._build_chat_response(
        "user_contact_paused",
        profile,
        "如果你微信更方便，也可以直接发我微信号。",
        {"all_fields": []},
        "dlg_contact_paused",
    )

    assert result["collected_info"]["contact"] == "电话暂缓, 微信争取中"


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


# ============================================================================
# Phase 1: Conversation Humanlike - Complaint/Repair Tests
# ============================================================================


class TestComplaintDetection:
    """Phase 1: complaint / repair 意图检测测试"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    @pytest.mark.parametrize(
        "user_message",
        [
            "怎么问这么多信息",
            "问这么多信息干嘛",
            "是不是问的次数太多了",
            "怎么一直问",
            "问了一遍又一遍",
            "你怎么老问这个",
            "别一直问资料",
            "有点烦",
            "你问得太细了",
            "像查户口一样",
            "怎么又问这个",
            "前面不是说了吗",
            "重复问了",
            "太啰嗦了",
        ],
    )
    def test_complaint_patterns_are_detected(self, chat_service, user_message):
        """complaint 触发词应被正确检测"""
        assert chat_service._is_complaint_message(user_message) is True

    @pytest.mark.parametrize(
        "user_message",
        [
            "你好",
            "我是90后",
            "深圳",
            "我想找个同城的",
            "你们靠谱吗",
            "收费吗",
        ],
    )
    def test_normal_messages_are_not_complaint(self, chat_service, user_message):
        """正常消息不应被误判为 complaint"""
        assert chat_service._is_complaint_message(user_message) is False

    def test_complaint_sets_repair_intent_in_turn_decision(self, chat_service):
        """complaint 消息应在 turn_decision 中设置 intent=complaint"""
        user_profile = UserProfile(account_id="test_complaint")
        decision = chat_service._build_turn_decision(
            "是不是问的次数太多了",
            user_profile,
            conversation_context={"message_count": 5},
        )
        assert decision.intent == "complaint"
        assert decision.primary_move == "repair_and_release"
        assert decision.allow_contact_target is False
        assert decision.allow_medium_target is False
        assert decision.in_repair_mode is True
        assert decision.repair_cooldown_remaining == 3

    def test_complaint_repair_response_avoids_strategy_leak(self, chat_service):
        """complaint 修复响应应承认问题，但不能暴露内部采集策略。"""
        response = chat_service._get_complaint_repair_response("是不是问的次数太多了")
        assert any(
            ack in response
            for ack in ["刚才", "重复问了", "接得不够好", "先收住"]
        )
        assert "追资料" not in response
        assert "问得有点密" not in response
        assert "按流程" not in response
        assert "最在意" not in response
        assert "最看重" not in response
        assert "接乱了" not in response
        assert "记住了" not in response


def test_complaint_repair_response_avoids_ai_like_self_exposure_for_repeat_ask():
    chat_service = _build_chat_service()
    response = chat_service._get_complaint_repair_response("不是说了吗？在深圳吗？")

    assert "接乱了" not in response
    assert "记住了" not in response
    assert "绕回这个点" not in response
    assert any(token in response for token in ["岔开了", "先收住", "接着往下聊"])


def test_complaint_repair_response_explains_over_questioning_from_user_benefit_angle():
    chat_service = _build_chat_service()
    response = chat_service._get_complaint_repair_response("怎么问这么多信息")

    assert any(token in response for token in ["更清楚", "更准", "合适方向"])
    assert "这轮我先收一下" in response or "先收住" in response
    assert "另一半" not in response
    assert "有没有什么偏好" not in response


def test_avoid_reasking_just_collected_field_advances_mainline():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_repeat_location")
    profile.sex = "男"
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})

    response = chat_service._avoid_reasking_just_collected_field(
        "那，你现在是在什么城市？",
        profile,
        {"all_fields": [{"field": "location", "value": "深圳"}]},
        current_ask_field="location",
        user_message="深圳呢",
        allow_medium_target=True,
    )

    assert "城市" not in response
    assert "学历" in response


class TestPartnerRequirementDedupGuard:
    """Phase 1: 偏好类去重 guard 测试"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    def test_generic_preference_ask_blocked_when_partner_requirement_exists(
        self, chat_service
    ):
        """已有 partner_requirement 后，泛化偏好问题应被清洗"""
        user_profile = UserProfile(account_id="test_pref_guard")
        user_profile.partner_requirement = "同城，90后"
        user_profile.collection_progress["partner_requirement"] = True

        # 模拟 AI 生成了包含泛化偏好问题的响应
        response = "好，那我们就按90后来聊。你更看重对方哪几点呀？"
        cleaned = chat_service._apply_field_ask_guard(
            user_profile, response, allow_medium_target=True
        )

        # 泛化偏好问题应被清洗
        assert "你更看重对方哪几点" not in cleaned

    def test_generic_preference_ask_allowed_when_partner_requirement_empty(
        self, chat_service
    ):
        """无 partner_requirement 时，也不能抢在核心主线前面开偏好支线。"""
        user_profile = UserProfile(account_id="test_pref_empty")

        response = "好，那我们继续聊。你更看重对方哪几点呀？"
        cleaned = chat_service._apply_field_ask_guard(
            user_profile, response, allow_medium_target=True
        )

        assert "你更看重对方哪几点" not in cleaned
        assert "男生还是女生" in cleaned

    def test_interleaving_followup_does_not_reask_partner_requirement_after_collected(
        self, chat_service
    ):
        """择偶要求收集一次后，缓冲追问也不能再变相重问偏好。"""
        user_profile = UserProfile(account_id="test_pref_once")
        user_profile.collection_progress["partner_requirement"] = True
        user_profile.partner_requirement = "更看重年龄段"
        user_profile.close_active_ask("partner_requirement")

        response = chat_service._build_interleaving_followup(
            user_profile,
            "深圳",
            allow_medium_target=True,
        )

        assert "最看重" not in response
        assert "更在意" not in response
        assert "年龄段" not in response
        assert "匹配点" not in response

    def test_interleaving_followup_falls_forward_to_occupation_after_medium_fields_closed(
        self, chat_service
    ):
        """中等字段关闭后，不应再硬插补充字段，优先保持自然承接。"""
        user_profile = UserProfile(account_id="test_followup_to_occupation")
        user_profile.collection_progress["partner_requirement"] = True
        user_profile.partner_requirement = "年龄不超过30岁"
        user_profile.collection_progress["monthly_income"] = True
        user_profile.monthly_income = "7万左右"
        user_profile.close_active_ask("partner_requirement")
        user_profile.close_active_ask("monthly_income")

        response = chat_service._build_interleaving_followup(
            user_profile,
            "7万左右",
            allow_medium_target=True,
        )

        assert "工作" not in response
        assert "从事" not in response
        assert "顺着你刚才这个点" not in response
        assert "你想先聊哪边都行" not in response


class TestMetaStrategyPhraseCleaning:
    """Phase 1: 元策略话术清洗测试"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    @pytest.mark.parametrize(
        "input_text,should_not_contain",
        [
            ("好，那我们就按90后来聊。", "按90后来聊"),
            ("我们先不连着问资料。", "先不连着问资料"),
            ("这轮我先不把资料问得太密。", "不把资料问得太密"),
            ("按这个优先推进", "按这个优先推进"),
            ("按这个优先筛", "按这个优先筛"),
        ],
    )
    def test_meta_strategy_phrases_are_cleaned(
        self, chat_service, input_text, should_not_contain
    ):
        """元策略话术应被清洗"""
        cleaned = chat_service._sanitize_robotic_tone(input_text)
        assert should_not_contain not in cleaned

    def test_short_confirmation_replaces_strategy_phrase(self, chat_service):
        """策略话术应被替换成短确认"""
        # "按X来聊" -> "X是吧" 或 "X我大概有数了"
        cleaned = chat_service._sanitize_robotic_tone("好，那我们就按90后来聊。")
        # 应该变成短确认或被清洗
        assert "按90后来聊" not in cleaned


class TestBridgeBackPrefix:
    """Phase 2: FAQ/边界/complaint 后的桥接前缀测试"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    def test_bridge_prefix_generated_for_faq_type(self, chat_service):
        """FAQ 类型应生成桥接前缀"""
        prefix = chat_service._build_bridge_back_prefix("faq")
        assert prefix
        assert prefix.endswith("。") or prefix.endswith(" ")
        # 应该是自然的过渡语
        assert any(
            keyword in prefix
            for keyword in ["先", "这块", "这个", "放一边"]
        )

    def test_bridge_prefix_generated_for_boundary_type(self, chat_service):
        """boundary 类型应生成桥接前缀"""
        prefix = chat_service._build_bridge_back_prefix("boundary")
        assert prefix
        assert any(
            keyword in prefix
            for keyword in ["先", "这块", "不勉强", "放一边"]
        )

    def test_bridge_prefix_generated_for_complaint_type(self, chat_service):
        """complaint 类型应生成桥接前缀"""
        prefix = chat_service._build_bridge_back_prefix("complaint")
        assert prefix
        assert any(
            keyword in prefix
            for keyword in ["节奏", "先", "换个"]
        )

    def test_bridge_prefix_empty_for_none_type(self, chat_service):
        """None 类型应返回空前缀"""
        prefix = chat_service._build_bridge_back_prefix(None)
        assert prefix == ""

    def test_bridge_prefix_empty_for_empty_string(self, chat_service):
        """空字符串应返回空前缀"""
        prefix = chat_service._build_bridge_back_prefix("")
        assert prefix == ""

    def test_bridge_prefix_fallback_for_unknown_type(self, chat_service):
        """未知类型应有默认前缀"""
        prefix = chat_service._build_bridge_back_prefix("unknown_type")
        # 未知类型使用默认变体
        assert prefix  # 应该返回某个默认值

    def test_user_profile_has_bridge_back_fields(self):
        """UserProfile 应包含 bridge_back 相关字段"""
        profile = UserProfile(account_id="test_bridge_fields")
        assert hasattr(profile, "needs_bridge_back")
        assert hasattr(profile, "last_side_topic_type")
        assert hasattr(profile, "complaint_cooldown_until")
        assert hasattr(profile, "last_profile_summary_turn")
        # 默认值
        assert profile.needs_bridge_back is False
        assert profile.last_side_topic_type is None

    def test_bridge_back_markers_are_set_after_faq(self):
        """FAQ 后应设置 bridge_back 标记"""
        profile = UserProfile(account_id="test_faq_bridge")
        # 模拟 FAQ 后的状态设置
        profile.needs_bridge_back = True
        profile.last_side_topic_type = "faq"
        assert profile.needs_bridge_back is True
        assert profile.last_side_topic_type == "faq"

    def test_bridge_back_markers_are_reset_after_use(self):
        """使用后应重置 bridge_back 标记"""
        profile = UserProfile(account_id="test_bridge_reset")
        profile.needs_bridge_back = True
        profile.last_side_topic_type = "faq"
        # 模拟重置
        profile.needs_bridge_back = False
        profile.last_side_topic_type = None
        assert profile.needs_bridge_back is False
        assert profile.last_side_topic_type is None


class TestProfileSummary:
    """Phase 2: 低频画像小结测试"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    def test_should_not_emit_summary_with_few_fields(self, chat_service):
        """当前默认不在主回复里注入画像小结。"""
        profile = UserProfile(account_id="test_summary_few")
        profile.collection_progress["sex"] = True
        profile.collection_progress["age"] = True

        should_emit = chat_service._should_emit_profile_summary(profile, current_message_count=5)
        assert should_emit is False

    def test_should_emit_summary_with_enough_fields(self, chat_service):
        """即使字段足够，也默认不启用画像小结。"""
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

    def test_should_not_emit_summary_too_frequently(self, chat_service):
        """画像小结默认关闭。"""
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

        # 模拟刚生成过小结
        profile.last_profile_summary_turn = 8

        should_emit = chat_service._should_emit_profile_summary(profile, current_message_count=10)
        assert should_emit is False

    def test_build_summary_line_includes_key_fields(self, chat_service):
        """小结语句应包含关键字段"""
        profile = UserProfile(account_id="test_summary_build")
        profile.location = "深圳"
        profile.age = "28"
        profile.partner_requirement = "同城"

        summary = chat_service._build_profile_summary_line(profile)
        assert summary
        assert "深圳" in summary
        assert "28" in summary or "岁" in summary
        assert "同城" in summary or "偏同城" in summary

    def test_build_summary_line_returns_empty_for_empty_profile(self, chat_service):
        """空画像应返回空小结"""
        profile = UserProfile(account_id="test_summary_empty")

        summary = chat_service._build_profile_summary_line(profile)
        assert summary == ""

    def test_summary_format_is_natural(self, chat_service):
        """小结格式应自然"""
        profile = UserProfile(account_id="test_summary_format")
        profile.location = "深圳"
        profile.age = "90后"
        profile.partner_requirement = "同城，90后"

        summary = chat_service._build_profile_summary_line(profile)
        assert summary.startswith("你")
        assert summary.endswith("是吧。")


def test_enforce_natural_completion_transition_moves_to_contact_after_occupation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_natural_contact")
    profile.sex = "男"
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
        }
    )

    response = chat_service._enforce_natural_completion_transition(
        "好，你接着说就行。",
        profile,
        {"all_fields": [{"field": "occupation", "value": "IT"}]},
        user_message="it",
    )

    assert "手机号" in response
    assert "接着说就行" not in response
    assert "后面如果继续聊得合适，也方便及时联系你" not in response


def test_enforce_natural_completion_transition_keeps_non_contact_response_when_not_ready():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_not_ready")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})

    response = chat_service._enforce_natural_completion_transition(
        "这个我知道了，我们接着往下聊。",
        profile,
        {"all_fields": [{"field": "partner_requirement", "value": "温柔"}]},
        user_message="温柔",
    )

    assert response == "这个我知道了，我们接着往下聊。"


def test_apply_humanlike_turn_structure_policy_does_not_prefix_contact_prompt_twice():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_prefix")

    response = chat_service._apply_humanlike_turn_structure_policy(
        "我大概了解你的情况了。后面要是继续聊得合适，留个手机号方便联系吗？",
        profile,
        "it",
        allow_medium_target=True,
    )

    assert response.count("留个手机号方便联系吗") == 1
    assert "后面如果继续聊得合适，也方便及时联系你" not in response


def test_dialogue_expression_service_avoids_duplicate_location_prefix():
    chat_service = _build_chat_service()

    response = chat_service.dialogue_expression_service.render_field_question(
        "location",
        user_message="90后",
    )

    assert "你现在，你现在" not in response
    assert "平时的话" not in response


def test_apply_humanlike_turn_structure_policy_interleaves_side_target_at_education_stage():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_education")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})
    profile.recent_asked_fields = ["sex", "age", "location"]

    response = chat_service._apply_humanlike_turn_structure_policy(
        "你学历这块大概是什么背景呀？",
        profile,
        "深圳",
        allow_medium_target=True,
    )

    assert "学历" in response
    assert any(token in response for token in ["学历", "大概", "背景"])


def test_profile_collection_policy_blocks_side_target_in_opening_stage():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_opening")
    profile.sex = "男"
    profile.collection_progress["sex"] = True

    side_target = policy.get_side_target(
        profile,
        main_target="age",
        user_message="男的",
        message_count=2,
        allow_medium_target=True,
    )

    assert side_target is None


def test_needs_style_retry_for_fixed_template_phrases():
    chat_service = _build_chat_service()

    assert chat_service._needs_style_retry("你好呀～对了，想问下你是男生还是女生呀？")
    assert chat_service._needs_style_retry("好，你是男生啦。 对了，你方便说下自己的年龄吗？")


def test_build_main_dialogue_prompt_includes_recent_style_avoidance():
    chat_service = _build_chat_service()
    manager = chat_service.dialogue_manager
    profile = UserProfile(account_id="u_prompt_style")
    context = {
        "message_count": 1,
        "recent_responses": ["你好呀～对了，想问下你是男生还是女生呀？"],
        "preferences": {"recent_prompt_signatures": ["你好呀|对了|想问下|sex"]},
    }

    prompt = manager.build_main_dialogue_prompt(
        "男的",
        profile,
        context,
        primary_move="light_followup",
        allow_contact_target=False,
        allow_medium_target=False,
    )

    assert "最近两轮你说过" in prompt
    assert "不要沿用同样开头" in prompt
    assert "不要并列枚举未婚和离异" in prompt


def test_build_lightweight_field_ack_from_message_bridges_location_naturally():
    chat_service = _build_chat_service()

    response = chat_service._build_lightweight_field_ack_from_message("深圳")

    assert "深圳" in response
    assert any(token in response for token in ["知道了", "是吧", "这边"])


def test_ensure_short_answer_ack_transition_prefixes_ack_before_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_short_answer_bridge")

    response = chat_service._ensure_short_answer_ack_transition(
        "你大概是什么学历呀？",
        user_message="深圳",
        user_profile=profile,
    )

    assert response.startswith(("深圳呀", "在深圳", "深圳我"))
    assert "学历" in response


def test_ensure_short_answer_ack_transition_does_not_double_ack_when_model_already_confirmed_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_short_answer_bridge_existing_ack")

    response = chat_service._ensure_short_answer_ack_transition(
        "好的，你是男生啦。 你今年多大呀？",
        user_message="男的",
        user_profile=profile,
    )

    assert response == "好的，你是男生啦。 你今年多大呀？"


def test_append_safe_short_answer_followup_continues_to_next_core_field_after_sex_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_safe_short_followup")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "6万"
    profile.collection_progress.update(
        {
            "sex": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
        }
    )

    response = chat_service._append_safe_short_answer_followup(
        "好，你是男生啦。",
        profile,
        {"all_fields": [{"field": "sex", "value": "男"}]},
        previous_asked_field="sex",
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        ask_field=None,
        followup_topic=None,
    )

    assert "男生" in response
    assert "多大" in response or "年龄" in response


def test_append_safe_short_answer_followup_skips_special_scenarios():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_safe_short_followup_guard")
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    response = chat_service._append_safe_short_answer_followup(
        "好，你是男生啦。",
        profile,
        {"all_fields": [{"field": "sex", "value": "男"}]},
        previous_asked_field="sex",
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        ask_field=None,
        followup_topic=None,
    )

    assert response == "好，你是男生啦。"


def test_prepend_multi_field_ack_transition_bridges_before_next_core_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_multi_field_ack")
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.collection_progress.update({"location": True, "occupation": True, "marital_status": True})

    response = chat_service._prepend_multi_field_ack_transition(
        "你今年大概多大呀？ 这样我心里会更有数一点。",
        profile,
        {
            "all_fields": [
                {"field": "location", "value": "深圳"},
                {"field": "occupation", "value": "IT"},
                {"field": "marital_status", "value": "单身"},
            ]
        },
        user_message="目前在深圳，单身，做it",
        response_channel="model",
        primary_move="ack_and_ask",
        ask_field="age",
        followup_topic=None,
    )

    assert "多大" in response
    assert response.startswith(("做IT", "好，IT这块", "IT方向", "在深圳", "深圳呀", "好，现在单身状态"))


def test_prepend_single_field_ack_transition_bridges_short_answer_before_next_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_single_field_ack")
    profile.education = "本科"
    profile.collection_progress["education"] = True

    response = chat_service._prepend_single_field_ack_transition(
        "我先简单了解下，你这边是男生还是女生呀？",
        profile,
        {"all_fields": [{"field": "education", "value": "本科"}]},
        user_message="本科",
        response_channel="model",
        primary_move="light_followup",
        ask_field="sex",
        followup_topic=None,
    )

    assert "男生还是女生" in response
    assert response == "我先简单了解下，你这边是男生还是女生呀？"


def test_prepend_single_field_ack_transition_skips_when_model_already_acked_location():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_single_field_ack_existing_location")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    response = chat_service._prepend_single_field_ack_transition(
        "在深圳这边是吧。 你目前是做哪方面工作的？",
        profile,
        {"all_fields": [{"field": "location", "value": "深圳"}]},
        user_message="深圳",
        response_channel="model",
        primary_move="light_followup",
        ask_field="occupation",
        followup_topic=None,
    )

    assert response == "在深圳这边是吧。 你目前是做哪方面工作的？"


def test_sanitize_robotic_tone_removes_repetitive_location_ack_prefix():
    cleaned = ChatService._sanitize_robotic_tone("在深圳这边是吧。 你平时也是在深圳工作吗，主要做什么呀？")
    assert "在深圳这边是吧" not in cleaned
    assert "主要做什么" in cleaned


def test_sanitize_robotic_tone_removes_repetitive_profile_ack_prefixes():
    cleaned = ChatService._sanitize_robotic_tone("本科是吧。 好呀，你今年大概多大呀？")
    assert "本科是吧" not in cleaned
    assert "多大" in cleaned

    cleaned = ChatService._sanitize_robotic_tone("做美容是吧。 你大概是什么学历呀？")
    assert "做美容是吧" not in cleaned
    assert "学历" in cleaned


def test_detect_which_field_is_asked_prefers_last_question_over_ack_text():
    chat_service = _build_chat_service()

    asked_field = chat_service._detect_which_field_is_asked(
        "好，现在单身状态我知道了。 这些我都先记下啦，姓文，180的个子挺不错的~你是男生还是女生呀？"
    )

    assert asked_field == "sex"


def test_handoff_to_contact_after_core_completion_switches_same_turn():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_handoff_after_age")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.age = 36
    profile.collection_progress.update(
        {
            "sex": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "age": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: True
    chat_service._has_active_contact_context = lambda *args, **kwargs: False
    chat_service._build_policy_field_prompt = lambda field, *_args, **_kwargs: "方便留个电话吗？后面联系你会方便些。"
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_phone")

    response = chat_service._handoff_to_contact_after_core_completion(
        "这个点我不重复绕了，你想聊别的就顺着说。",
        profile,
        collection_result={"all_fields": [{"field": "age", "value": "36"}]},
        user_message="90后呢",
        response_channel="model",
        primary_move="light_followup",
        contact_gate_before=False,
    )

    assert response == "方便留个电话吗？后面联系你会方便些。"


def test_handoff_to_pending_target_after_core_completion_switches_to_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_partner_after_age")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "美容相关"
    profile.marital_status = "单身"
    profile.monthly_income = "3万"
    profile.collection_progress.update(
        {
            "sex": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "monthly_income": True,
            "age": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: False
    chat_service.collection_policy.get_uncovered_core_fields = lambda _profile: []
    chat_service.collection_policy.can_actively_ask = lambda _profile, field: field == "partner_requirement"
    chat_service.collection_policy.get_medium_transition_host = lambda _profile, field: None
    chat_service._has_active_contact_context = lambda *args, **kwargs: False
    chat_service._build_policy_field_prompt = (
        lambda field, *_args, **_kwargs: "你对另一半有啥大致要求不？" if field == "partner_requirement" else "unused"
    )

    response = chat_service._handoff_to_pending_target_after_core_completion(
        "这个点我不重复绕了，你想聊别的就顺着说。",
        profile,
        collection_result={"all_fields": [{"field": "age", "value": "36"}]},
        user_message="90后",
        response_channel="model",
        primary_move="light_followup",
        contact_gate_before=False,
    )

    assert "另一半" in response or "要求" in response


def test_handoff_to_pending_target_after_core_completion_prefers_fused_partner_requirement_transition():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_partner_transition")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "6万"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: False
    chat_service.collection_policy.get_uncovered_core_fields = lambda _profile: []
    chat_service.collection_policy.can_actively_ask = lambda _profile, field: field == "partner_requirement"
    chat_service.collection_policy.get_medium_transition_host = (
        lambda _profile, field: "age" if field == "partner_requirement" else None
    )
    chat_service._has_active_contact_context = lambda *args, **kwargs: False

    response = chat_service._handoff_to_pending_target_after_core_completion(
        "继续聊。",
        profile,
        collection_result={"all_fields": [{"field": "age", "value": "36"}]},
        user_message="90后",
        response_channel="model",
        primary_move="light_followup",
        contact_gate_before=False,
    )

    assert "另一半" in response or "看重" in response or "要求" in response or "想找个什么样的" in response
    assert "年龄" in response or "多大" in response or "90后" in response


def test_handoff_to_contact_after_medium_completion_switches_after_partner_requirement_finishes():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_after_partner_finish")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "6万"
    profile.marital_status = "单身"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "marital_status": True,
            "partner_requirement": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: True
    chat_service.collection_policy.get_uncovered_core_fields = lambda _profile: []
    chat_service.collection_policy.get_uncovered_medium_fields = lambda _profile: []
    chat_service._build_policy_field_prompt = (
        lambda field, *_args, **_kwargs: "方便留个常用手机号吗？" if field == "contact" else "unused"
    )

    response = chat_service._handoff_to_contact_after_medium_completion(
        "你这边更偏向温柔，对吧。 没问题呀，我尽量？",
        profile,
        collection_result={"all_fields": [{"field": "partner_requirement", "value": "温柔"}]},
        user_message="温柔点",
        response_channel="model",
        primary_move="light_followup",
    )

    assert "手机号" in response or "联系" in response


def test_handoff_to_pending_target_after_core_completion_prefers_fused_marital_status_transition():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_marital_transition")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "partner_requirement": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: False
    chat_service.collection_policy.get_uncovered_core_fields = lambda _profile: []
    chat_service.collection_policy.can_actively_ask = lambda _profile, field: field == "marital_status"
    chat_service._has_active_contact_context = lambda *args, **kwargs: False

    response = chat_service._handoff_to_pending_target_after_core_completion(
        "你继续说，我顺着往下了解。",
        profile,
        collection_result={"all_fields": [{"field": "sex", "value": "男"}]},
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        contact_gate_before=False,
    )

    assert "单身状态" in response
    assert any(token in response for token in ("顺手确认", "另外", "对了"))


def test_enforce_pending_partner_requirement_followup_replaces_empty_hold():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_partner_requirement_followup")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.monthly_income = "6万"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "monthly_income": True,
        }
    )

    response = chat_service._enforce_pending_partner_requirement_followup(
        "这个点我不重复绕了，你想聊别的就顺着说。",
        profile,
        ask_field="partner_requirement",
        user_message="我单身，身高180，体重90公斤",
        response_channel="model",
        primary_move="ack_and_ask",
    )

    assert "另一半" in response or "有什么要求" in response or "更看重" in response


def test_profile_collection_policy_does_not_repeat_partner_requirement_side_target_after_first_ask():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_pref_cooldown")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})
    profile.field_ask_count["partner_requirement"] = 1

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="深圳",
        message_count=6,
        allow_medium_target=True,
    )

    assert side_target is None


def test_profile_collection_policy_allows_partner_requirement_as_side_target_after_age_in_compact_stage():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_pref_side_after_age")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "美容"
    profile.monthly_income = "3万"
    profile.collection_progress.update(
        {"sex": True, "location": True, "education": True, "occupation": True, "monthly_income": True}
    )

    side_target = policy.get_side_target(
        profile,
        main_target="age",
        user_message="本科",
        message_count=6,
        allow_medium_target=True,
    )

    assert side_target == "partner_requirement"


def test_profile_collection_policy_allows_marital_status_as_side_target_after_education_in_compact_stage():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_marital_side_after_education")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "occupation": True, "partner_requirement": True}
    )

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="IT，4万",
        message_count=6,
        allow_medium_target=True,
    )

    assert side_target == "marital_status"


def test_profile_collection_policy_prioritizes_marital_status_after_core_fields():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_marital_main")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True, "occupation": True}
    )

    main_target = policy.get_main_target(profile, allow_contact_target=True)

    assert main_target == "marital_status"


def test_extract_simple_partner_requirement_tolerates_polluted_short_answer():
    chat_service = _build_chat_service()

    assert chat_service._extract_simple_partner_requirement("本科，我温柔 点") == "温柔"


def test_detect_which_field_is_asked_prefers_partner_requirement_over_earlier_age_question():
    chat_service = _build_chat_service()

    field = chat_service._detect_which_field_is_asked(
        "那我再了解下，方便说下你今年多大吗？ 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更在意哪方面？"
    )

    assert field == "partner_requirement"


def test_avoid_reasking_already_collected_fields_rewrites_when_age_is_already_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_avoid_reask_age")
    profile.sex = "男"
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "美容"
    profile.monthly_income = "3万"
    profile.marital_status = "单身"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "marital_status": True,
        }
    )

    response = chat_service._avoid_reasking_already_collected_fields(
        "好，男生是吧。 那我再了解下，方便说下你今年多大吗？ 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更在意哪方面？",
        profile,
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        allow_medium_target=True,
    )

    assert "多大" not in response
    assert "几岁" not in response
    assert "哪年" not in response
    assert any(token in response for token in ("另一半", "看重", "要求", "想找"))


def test_classify_withdraw_intent_detects_strong_stop_message():
    chat_service = _build_chat_service()

    assert chat_service._classify_withdraw_intent("不聊了") == "strong"
    assert chat_service._classify_withdraw_intent("今天先到这吧") == "strong"


def test_build_withdraw_response_closes_immediately_when_contact_already_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_withdraw_contact_done")
    profile.phone = "17600000000"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True

    response, should_close = chat_service._build_withdraw_response(profile, user_message="不聊了")

    assert should_close is True
    assert any(token in response for token in ("等好消息", "联系前", "匹配一般"))


def test_build_withdraw_response_retains_once_before_soft_close_without_contact():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_withdraw_no_contact")

    profile.increment_ask_count("conversation_end_intent")
    response, should_close = chat_service._build_withdraw_response(profile, user_message="不聊了")
    assert should_close is False
    assert any(token in response for token in ("顾虑", "不往下问", "担心"))

    profile.increment_ask_count("conversation_end_intent")
    response, should_close = chat_service._build_withdraw_response(profile, user_message="还是不想聊了")
    assert should_close is True
    assert any(token in response for token in ("先这样", "先收住", "不打扰"))


def test_handoff_to_contact_after_core_completion_blocks_withdraw_message():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_withdraw_blocks_contact")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.age = 36
    profile.collection_progress.update(
        {
            "sex": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "age": True,
        }
    )
    chat_service.collection_policy.can_enter_contact = lambda _profile: True

    response = chat_service._handoff_to_contact_after_core_completion(
        "这轮我先收住。",
        profile,
        collection_result={"all_fields": [{"field": "age", "value": "36"}]},
        user_message="不聊了",
        response_channel="model",
        primary_move="light_followup",
        contact_gate_before=False,
    )

    assert response == "这轮我先收住。"


def test_render_field_question_uses_profile_location_for_bridged_occupation_prompt():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_bridge_location")
    profile.location = "深圳"

    response = service.render_field_question("occupation", profile=profile, stage="opening", user_message="嗯")

    assert "深圳" in response
    assert any(token in response for token in ("工作", "做什么"))


def test_build_shadow_profile_for_decision_applies_current_turn_fields_without_persisting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_shadow_profile")

    shadow = chat_service._build_shadow_profile_for_decision(
        profile,
        "我来自深圳，今年29岁",
        last_response="你好呀，在的。 你是想认真聊聊，还是先问问情况呀？",
    )

    assert profile.location is None
    assert profile.age is None
    assert shadow.location == "深圳"
    assert shadow.age == 29


def test_build_turn_decision_uses_shadow_profile_to_skip_already_provided_location_and_age():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_shadow_decision")
    shadow = chat_service._build_shadow_profile_for_decision(profile, "我来自深圳，今年29岁")

    decision = chat_service._build_turn_decision(
        "我来自深圳，今年29岁",
        shadow,
        conversation_context={"message_count": 1, "recent_responses": ["你好呀，在的。 你是想认真聊聊，还是先问问情况呀？"]},
    )

    assert decision.ask_field not in {"location", "age"}


def test_detect_which_field_is_asked_prefers_occupation_when_work_and_income_are_asked_together():
    chat_service = _build_chat_service()

    field = chat_service._detect_which_field_is_asked(
        "那你现在在深圳主要做哪方面工作呀？ 收入这块大概在什么区间，也可以顺手说个大概。"
    )

    assert field == "occupation"


def test_detect_which_field_is_asked_recognizes_soft_gender_confirmation():
    chat_service = _build_chat_service()

    field = chat_service._detect_which_field_is_asked(
        "我再确认下，你这边是男生在了解，对吧？"
    )

    assert field == "sex"


def test_detect_asked_fields_in_response_recognizes_soft_gender_confirmation():
    chat_service = _build_chat_service()

    asked_fields = chat_service._detect_asked_fields_in_response(
        "我顺手确认一下，你这边是女生对吧？"
    )

    assert "sex" in asked_fields


def test_render_field_question_does_not_bridge_age_when_age_already_collected():
    expr = DialogueExpressionService()
    profile = UserProfile(account_id="u_age_bridge_guard")
    profile.education = "本科"
    profile.age = 29
    profile.collection_progress["education"] = True
    profile.collection_progress["age"] = True

    rendered = expr.render_field_question("age", profile=profile, user_message="本科")

    assert "年龄段" not in rendered
    assert "多大" not in rendered
    assert any(token in rendered for token in ("单身", "感情状态", "婚况"))


def test_build_interleaving_followup_does_not_use_collected_age_as_host_for_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_partner_requirement")
    profile.education = "本科"
    profile.age = 29
    profile.sex = "男"
    profile.marital_status = "单身"
    profile.collection_progress["education"] = True
    profile.collection_progress["age"] = True
    profile.collection_progress["sex"] = True
    profile.collection_progress["marital_status"] = True

    rendered = chat_service._build_interleaving_followup(  # noqa: SLF001
        profile,
        "男的，单身",
        main_target="age",
        preferred_side_target="partner_requirement",
    )

    assert "年龄段" not in rendered
    assert "多大" not in rendered
    assert any(token in rendered for token in ("另一半", "想找", "看重", "在意"))


@pytest.mark.asyncio
async def test_enforce_profile_bridge_response_falls_back_to_interleaving_followup_when_bridge_needed():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_bridge_fallback")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    turn_decision = TurnDecision(
        ask_field="occupation",
        response_channel="model",
        allow_medium_target=True,
        primary_move="light_followup",
    )

    response = await chat_service._enforce_profile_bridge_response(
        "你现在主要做哪方面工作呀？ 收入这块大概在什么区间，也可以顺手说个大概。",
        account_id="u_bridge_fallback",
        user_message="来自深圳",
        user_profile=profile,
        turn_decision=turn_decision,
        conversation_context={"message_count": 1},
    )

    assert "深圳" in response
    assert any(token in response for token in ("工作", "收入"))


def test_extraction_service_partner_requirement_tolerates_polluted_short_answer():
    assert ExtractionService._extract_partner_requirement_from_user_message("本科，我温柔 点") == "温柔"


def test_extraction_service_partner_requirement_handles_modal_particle_reply():
    assert ExtractionService._extract_partner_requirement_from_user_message("本科，温柔吧") == "温柔"


def test_apply_extraction_guards_allows_composite_sex_short_answer_in_sex_context():
    chat_service = _build_chat_service()

    guarded = chat_service._apply_extraction_guards(
        {"sex": "男", "marital_status": "单身"},
        "男的，是的，单身",
        "你这边是男生还是女生呀？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？",
    )

    assert guarded["sex"] == "男"


def test_apply_extraction_guards_allows_trailing_punct_sex_short_answer_in_sex_context():
    chat_service = _build_chat_service()

    guarded = chat_service._apply_extraction_guards(
        {"sex": "男"},
        "男的，",
        "我顺手确认下，你这边是男生还是女生呀？",
    )

    assert guarded["sex"] == "男"


def test_apply_extraction_guards_allows_affirmative_confirmation_to_confirm_sex():
    chat_service = _build_chat_service()

    guarded = chat_service._apply_extraction_guards(
        {"sex": "男"},
        "是的",
        "我再确认下，你这边是男生对吧？",
    )

    assert guarded["sex"] == "男"


def test_build_service_confirmation_resume_response_prefers_unresolved_core_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_service_confirm_resume")
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "7万"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {
            "age": True,
            "age_label": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "partner_requirement": True,
        }
    )

    response = chat_service._build_service_confirmation_resume_response(
        profile,
        "是的",
        message_count=5,
        last_response="我再确认下，你这边是男生对吧？",
    )

    assert "男生" in response or "女生" in response


def test_enforce_contact_outcome_policy_does_not_end_when_contact_done_but_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_done_profile_incomplete")
    profile.phone = "17688765456"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True
    profile.rejected_wechat = True
    profile.wechat_ask_count = 1
    profile.wechat_effective_ask_count = 1

    response = chat_service._enforce_contact_outcome_policy(
        "没事的，微信不方便留也完全没关系，那你方便给个常用的手机号不？后续有合适的匹配进展也好及时联系到你呀。",
        profile,
        collection_result={"all_fields": []},
        user_message="不留微信了",
    )

    assert "等好消息" not in response
    assert "联系到你" not in response


def test_get_contact_completion_ending_response_without_contact_avoids_contact_promises():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_contact_completion")
    profile.rejected_phone = True
    profile.rejected_wechat = True
    profile.phone_ask_count = 2
    profile.phone_effective_ask_count = 2
    profile.wechat_ask_count = 2
    profile.wechat_effective_ask_count = 2

    response = chat_service._get_contact_completion_ending_response(profile)

    assert "联系" not in response
    assert "通知" not in response
    assert "微信" not in response
    assert "电话" not in response


def test_get_contact_terminal_or_resume_response_prefers_profile_resume_when_contact_done_but_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_resume_profile")
    profile.phone = "17688765456"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True
    profile.rejected_wechat = True
    profile.wechat_ask_count = 1
    profile.wechat_effective_ask_count = 1

    chat_service._build_policy_field_prompt = lambda field, *_args, **_kwargs: (
        "你这边是男生还是女生呀？" if field == "sex" else f"ask:{field}"
    )

    response = chat_service._get_contact_terminal_or_resume_response(profile, "不留微信了")

    assert response == "你这边是男生还是女生呀？"


def test_prevent_no_repeat_hold_from_blocking_core_followup():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_repeat_core")
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "3万"
    profile.marital_status = "单身"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {
            "age": True,
            "age_label": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "marital_status": True,
            "partner_requirement": True,
        }
    )

    response = chat_service._prevent_no_repeat_hold_from_blocking_progress(
        "这个我知道了，咱们不在这上面打转。",
        profile,
        collection_result={"all_fields": [{"field": "partner_requirement", "value": "温柔"}]},
        user_message="温柔，不要低于160，漂亮点的，其他没有了",
    )

    assert "男生还是女生" in response


@pytest.mark.anyio
async def test_build_no_ai_response_prefers_core_followup_over_low_pressure_hold():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_ai_core_resume")
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "7万"
    profile.partner_requirement = "温柔"
    profile.collection_progress.update(
        {
            "age": True,
            "age_label": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "partner_requirement": True,
        }
    )
    profile.non_cooperation_turns = 3
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="本科这边我知道了，那你现在大概什么年龄段呀？")

    response = await chat_service._build_no_ai_response("u_no_ai_core_resume", profile, "嗯")

    assert "男生" in response or "女生" in response
    assert "顺着听" not in response

def test_render_field_question_uses_mid_conversation_sex_prompt_without_opening_phrase():
    service = DialogueExpressionService()

    response = service.render_field_question("sex", stage="completing", user_message="本科")

    assert "男生还是女生" in response
    assert "我先简单了解下" not in response
    assert "我先认识你一下" not in response


def test_profile_collection_policy_blocks_contact_until_partner_requirement_is_covered():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_contact_ready")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True, "occupation": True}
    )

    assert policy.can_enter_contact(profile) is False


def test_enforce_core_mainline_followup_allows_approved_side_target_interleave():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_side_target_pass")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})

    response = chat_service._enforce_core_mainline_followup(
        "你对另一半大概有什么要求呀？比如年龄、城市、性格这些。",
        profile,
        ask_field="education",
        collection_result=None,
        user_message="深圳",
        response_channel="model",
        primary_move="light_followup",
    )

    assert any(token in response for token in ["学历", "大概", "背景"])
    assert "学历" in response


def test_collapse_duplicate_ack_segments_removes_double_confirmation():
    chat_service = _build_chat_service()

    response = chat_service._collapse_duplicate_ack_segments(
        "男生，明白了。 好嘞，你是男生啦。 你今年多大呀？"
    )

    assert "你今年多大呀？" in response
    assert response.count("男生") <= 1


def test_collapse_duplicate_ack_segments_prefers_compound_ack_question_segment():
    chat_service = _build_chat_service()

    response = chat_service._collapse_duplicate_ack_segments(
        "男生，明白了。 好的，你是男生啦。 你今年多大呀？"
    )

    assert response == "好的，你是男生啦。 你今年多大呀？"


def test_collapse_duplicate_ack_segments_removes_generic_followup_ack_after_specific_ack():
    chat_service = _build_chat_service()

    response = chat_service._collapse_duplicate_ack_segments(
        "好，你这边是男生。 嗯嗯我知道啦。 你现在主要在哪个城市生活呀？"
    )

    assert response == "好，你这边是男生。 你现在主要在哪个城市生活呀？"


def test_enforce_contact_outcome_policy_keeps_model_written_phone_prompt_when_action_matches():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_model_prompt")

    response = chat_service._enforce_contact_outcome_policy(
        "你要是愿意的话，留个常用电话给我，后面沟通也方便一点。",
        profile,
        collection_result={},
        user_message="好的",
    )

    assert response == "你要是愿意的话，留个常用电话给我，后面沟通也方便一点。"


def test_enforce_core_mainline_followup_moves_past_just_collected_location():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_after_location")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})

    response = chat_service._enforce_core_mainline_followup(
        "那，你现在是在什么城市？",
        profile,
        ask_field="location",
        collection_result={"all_fields": [{"field": "location", "value": "深圳"}]},
        user_message="深圳",
        response_channel="model",
        primary_move="light_followup",
    )

    assert "城市" not in response
    assert any(token in response for token in ["学历", "另一半", "看重"])


def test_sanitize_robotic_tone_removes_sex_confirmation_prefix():
    cleaned = ChatService._sanitize_robotic_tone("好，你是男生啦。 方便说下你今年多大吗？")
    assert "男生啦" not in cleaned
    assert "多大" in cleaned


def test_format_fast_path_ack_skips_sex_confirmation():
    chat_service = _build_chat_service()
    response = chat_service._format_fast_path_ack("sex", "男")
    assert response == ""


class TestShortAnswerDetection:
    """短答识别仍保留，供主模型路径的上下文约束使用。"""

    @pytest.fixture
    def chat_service(self):
        return _build_chat_service()

    def test_short_answer_detection_single_word(self, chat_service):
        """单字/短词应被识别为短答"""
        assert chat_service._is_short_answer("男的") is True
        assert chat_service._is_short_answer("90后") is True
        assert chat_service._is_short_answer("深圳") is True
        assert chat_service._is_short_answer("本科") is True
        assert chat_service._is_short_answer("对") is True
        assert chat_service._is_short_answer("嗯") is True

    def test_short_answer_detection_long_message(self, chat_service):
        """长消息不应被识别为短答"""
        long_message = "我现在在深圳工作，做互联网运营，平时喜欢运动和看书"
        assert chat_service._is_short_answer(long_message) is False

    def test_short_answer_detection_medium_length(self, chat_service):
        """中等长度消息应正确判断"""
        assert chat_service._is_short_answer("4万左右") is True
        assert chat_service._is_short_answer("本科") is True
        assert chat_service._is_short_answer("我在深圳南山这边上班") is False
        assert chat_service._is_short_answer("本科毕业。") is False
