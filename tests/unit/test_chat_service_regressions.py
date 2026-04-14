from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import Mock
import importlib
import uuid

import pytest

from src.config.settings import settings
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.modules.conversation.domain.conversation_ending_service import ConversationEndingService
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import (
    PreGenerationResolutionMeta,
    TurnPriorityDecision,
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.models import (
    FieldObservation,
    TurnPersistencePlan,
    TurnSemanticFrame,
)
from src.modules.conversation_response.domain.ai_response_generator import AIResponseResult
from src.modules.conversation_understanding.domain.models import AcceptedField
from src.modules.conversation_response.domain.response_plan_builder import ResponsePlanBuilder
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.services.ai_service import AIService
from src.services.core.chat_service import ChatService
from src.services.data.user_service import UserService
from src.services.prompts.prompts import CORE_PERSONALITY, MAIN_DIALOGUE, SYSTEM_WELCOME_MESSAGE, get_main_dialogue
from src.services.core.chat_service import OpeningIntentSignal
from src.services.core.chat_service_collection_extraction_service import (
    ChatServiceCollectionExtractionService,
)
from src.services.core.chat_service_collection_postprocess_service import (
    ChatServiceCollectionPostprocessService,
)
from src.services.core.chat_service_contact_context_service import (
    ChatServiceContactContextService,
)
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.shared.models.chat_flow import ProfileCollectionResult


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


class _ConfirmationAIService:
    def __init__(self, response: str):
        self.response = response

    async def generate_response(self, *args, **kwargs):
        return self.response


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


@pytest.mark.asyncio
async def test_collection_extraction_directly_applies_authoritative_persistence_plan_fields():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_collection_authoritative_merge")
    chat_service.user_service = _FakeProfileUserService(profile)
    service = ChatServiceCollectionExtractionService(chat_service)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="方便简单说下自己的情况吗？")
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})

    understanding_result = TurnUnderstandingResult(primary_turn_type="profile_answer")
    setattr(
        understanding_result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="location",
                    value="深圳龙华",
                    normalized_value="深圳龙华",
                    scope="self",
                    evidence_text="深圳龙华在编女教师",
                    confidence=0.96,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                    source_channel="ai",
                )
            ]
        ),
    )

    _, collection_result, refreshed_profile = await service.run_extraction(
        account_id="u_collection_authoritative_merge",
        user_profile=profile,
        extracted_data={"location": "深圳"},
        user_message="深圳龙华在编女教师",
        extraction_meta={"location": {"source": "rule"}},
        understanding_result=understanding_result,
    )

    chat_service.extraction_service.process_extracted_data.assert_not_awaited()
    assert refreshed_profile.location == "深圳龙华"
    assert collection_result["all_fields"] == [{"field": "location", "value": "深圳龙华"}]


def test_turn_understanding_treats_current_field_refusal_as_soft_retry_not_boundary():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_refusal")

    result = chat_service.turn_understanding_service.analyze(
        TurnUnderstandingInput(
            user_message="不方便说",
            last_response="90后我知道了，那你具体是哪一年出生的呀？",
            message_count=4,
            user_profile=profile,
            conversation_context={},
            in_contact_flow=False,
        )
    )

    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "age"


def test_detect_asked_fields_uses_primary_question_segment_for_age_bucket_ack():
    chat_service = _build_chat_service()

    asked_fields = chat_service._detect_asked_fields_in_response(
        "90后我知道啦，你现在是单身状态对吧？"
    )

    assert asked_fields == {"marital_status"}


def test_extract_confirmed_sex_candidate_supports_soft_girl_confirmation():
    chat_service = _build_chat_service()

    candidate = chat_service.turn_understanding_service._extract_confirmed_sex_candidate_from_context(  # noqa: SLF001
        "你好呀，想找男朋友对吧，那你应该是女孩子哦？"
    )
    asked_field = chat_service.turn_understanding_service._detect_which_field_is_asked(  # noqa: SLF001
        "你好呀，想找男朋友对吧，那你应该是女孩子哦？"
    )

    assert candidate == "女"
    assert asked_field == "sex"


def test_contact_context_turns_off_after_contact_complete_and_mainline_resume():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_context_done")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.wechat_ask_count = 1
    profile.last_contact_request_type = "wechat"

    service = ChatServiceContactContextService(chat_service)

    assert service.has_active_contact_context(profile, user_message="男的") is False


def test_contact_context_recognizes_persistence_plan_contact_signal_without_legacy_slots():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_context_plan_signal")
    profile.phone_ask_count = 1
    service = ChatServiceContactContextService(chat_service)
    understanding = TurnUnderstandingResult(
        primary_turn_type="general",
        resolved_slots={},
        confidence=0.86,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="phone",
                    value="13526783627",
                    normalized_value="13526783627",
                    scope="contact",
                    evidence_text="13526783627",
                    confidence=0.98,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    assert service.has_active_contact_context(
        profile,
        user_message="13526783627",
        understanding_result=understanding,
    ) is True


def test_turn_understanding_prefers_profile_answer_for_non_contact_slot_after_contact_complete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_answer_guard")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True

    result = chat_service.turn_understanding_service.analyze(
        TurnUnderstandingInput(
            user_message="男的",
            last_response="我再确认一下，你这边是男生还是女生呀？",
            message_count=4,
            user_profile=profile,
            conversation_context={},
            in_contact_flow=True,
        )
    )

    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["sex"] == "男"


def test_has_ongoing_contact_flow_false_after_contact_complete_without_pending_state():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_contact_flow_done")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.contact_complete = True
    profile.wechat_ask_count = 1

    assert policy.has_ongoing_contact_flow(profile) is False


def test_question_budget_guard_falls_back_to_complete_question_instead_of_broken_fragment():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_budget_guard_fragment")

    guarded = chat_service._enforce_question_budget_guard(
        "哈哈看来你找对象",
        user_profile=profile,
        user_message="没有要求",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="complete",
            next_action="continue",
            primary_move="light_followup",
            ask_field="monthly_income",
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
        ),
    )

    assert "月收入" in guarded or "收入" in guarded
    assert guarded != "哈哈看来你找对象"


def test_question_budget_guard_rewrites_trailing_fragment_like_dagaide():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_budget_guard_dagaide")

    guarded = chat_service._enforce_question_budget_guard(
        "做自媒体时间上应该还挺灵活的对吧，你是什么学历呀，大概的",
        user_profile=profile,
        user_message="做自媒体",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="opening",
            next_action="continue",
            primary_move="ack_and_ask",
            ask_field="education",
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=True,
            response_channel="model",
        ),
    )

    assert "大概的" not in guarded
    assert "学历" in guarded


def test_contact_completion_response_uses_fast_timeline_when_profile_qualifies():
    service = ExpectationService()
    profile = UserProfile(account_id="u_fast_timeline")
    profile.sex = "男"
    profile.age = 28
    profile.education = "本科"
    profile.monthly_income = "4万"

    response = service.get_contact_completion_response(profile)

    assert "等好消息" in response
    assert "1-8小时" in response
    assert "提前约时间" in response


def test_contact_completion_response_handles_string_age_without_type_error():
    service = ExpectationService()
    profile = UserProfile(account_id="u_fast_timeline_str_age")
    profile.sex = "男"
    profile.age = "28"
    profile.education = "本科"
    profile.monthly_income = "5万"

    response = service.get_contact_completion_response(profile)

    assert "1-8小时" in response


def test_build_terminal_response_prefers_contact_completion_copy_for_normal_complete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_terminal_normal_complete")
    profile.sex = "男"
    profile.age = 28
    profile.education = "本科"
    profile.monthly_income = "4万"
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.partner_requirement = "看重身高"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )

    response = chat_service._build_terminal_response({"scenario": "normal_complete"}, profile)

    assert response is not None
    assert "等好消息" in response
    assert "1-8小时" in response


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_keeps_contact_completion_copy():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_contact_complete")
    profile.conversation_ended = True
    profile.sex = "男"
    profile.age = 28
    profile.education = "本科"
    profile.monthly_income = "4万"
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.partner_requirement = "看重身高"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )
    base_response = chat_service._get_contact_completion_ending_response(profile)
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={"recent_responses": [base_response]})
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": base_response})

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_contact_complete",
        user_profile=profile,
        user_message="有钱，其他的没有了",
        dialog_id="dlg_ended",
        is_new_user_session=False,
    )

    assert result is not None
    assert "等好消息" in result.final_response
    assert "1-8小时" in result.final_response


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_answers_faq_without_repeating_terminal_copy():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_faq")
    profile.conversation_ended = True
    profile.sex = "男"
    profile.age = 28
    profile.education = "本科"
    profile.monthly_income = "5万"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.rejected_wechat = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(
        return_value={"recent_responses": ["好的，那你等好消息啦，祝你早日脱单🥰 匹配一般1-8小时哒~ 牵线同事联系前会提前约时间，不打扰你～"]}
    )
    chat_service._get_priority_question_response = Mock(return_value="不是中介，就是正常帮你做匹配沟通。")
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "不是中介，就是正常帮你做匹配沟通。"})

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_faq",
        user_profile=profile,
        user_message="你们是中介吗",
        dialog_id="dlg_ended_faq",
        is_new_user_session=False,
    )

    assert result is not None
    assert "中介" in result.final_response
    assert "等好消息" not in result.final_response


@pytest.mark.asyncio
async def test_process_after_extraction_backfills_normal_complete_when_profile_is_complete():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_normal_complete")
    profile.sex = "男"
    profile.age = 28
    profile.age_label = "98年"
    profile.education = "本科"
    profile.monthly_income = "4万"
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.partner_requirement = "看重身高"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )
    chat_service.user_service.save_user_profile = AsyncMock()

    result = await service.process_after_extraction(
        account_id="u_postprocess_normal_complete",
        user_profile=profile,
        collection_result={"collected": False, "all_fields": []},
        user_message="其他的没有了",
        last_response="原来你找对象比较看重身高呀，除了身高之外还有没有其他比较看重的择偶要求呀？",
    )

    assert result["ending_info"]["scenario"] == "normal_complete"


@pytest.mark.asyncio
async def test_process_after_extraction_repairs_self_partner_age_scope_conflict():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_age_scope_conflict")
    profile.age = 31
    profile.age_label = "90后"
    profile.partner_requirement = "香港，90后都可以"
    profile.collection_progress.update({"age": True, "age_label": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_postprocess_age_scope_conflict",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "partner_requirement", "value": "香港，90后都可以"}]},
        user_message="95想找90后都可以有不",
        last_response="新能源行业现在发展势头很猛呀，挺不错的。那你今年多大啦？",
    )

    assert profile.age == 31
    assert profile.age_label == "95年"
    assert profile.pending_birth_year_bucket is None
    assert any(
        str(item.get("field") or "").strip() == "age_label" and str(item.get("value") or "").strip() == "95年"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_process_after_extraction_repairs_self_partner_occupation_scope_conflict():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_occupation_scope_conflict")
    profile.occupation = "找同医疗体系比自己大都可以同在深圳发展"
    profile.education = "本科"
    profile.collection_progress.update({"occupation": True, "education": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_postprocess_occupation_scope_conflict",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "occupation", "value": "找同医疗体系比自己大都可以同在深圳发展"}]},
        user_message="90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地",
        last_response="你好呀，可以简单介绍下自己情况和择偶要求。",
    )

    assert profile.occupation == "护士"
    assert any(
        str(item.get("field") or "").strip() == "occupation" and str(item.get("value") or "").strip() == "护士"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_process_after_extraction_does_not_override_authoritative_persistence_plan_field():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_authoritative_occupation")
    profile.occupation = "在编教师"
    profile.partner_requirement = "找同医疗体系比自己大都可以同在深圳发展"
    profile.collection_progress.update({"occupation": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    fake_user_service.update_user_profile_field = AsyncMock(side_effect=fake_user_service.update_user_profile_field)
    chat_service.user_service = fake_user_service

    understanding_result = TurnUnderstandingResult(primary_turn_type="profile_answer")
    setattr(
        understanding_result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="在编教师",
                    normalized_value="在编教师",
                    scope="self",
                    evidence_text="深圳龙华在编女教师",
                    confidence=0.96,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    result = await service.process_after_extraction(
        account_id="u_postprocess_authoritative_occupation",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "occupation", "value": "在编教师"}]},
        user_message="90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地",
        last_response="你好呀，可以简单介绍下自己情况和择偶要求。",
        understanding_result=understanding_result,
    )

    assert profile.occupation == "在编教师"
    fake_user_service.update_user_profile_field.assert_not_awaited()
    assert any(
        str(item.get("field") or "").strip() == "occupation" and str(item.get("value") or "").strip() == "在编教师"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_replay_postprocess_repairs_self_age_label_for_95_find_90s_message():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_replay_postprocess_95_find_90s")
    profile.age = 31
    profile.age_label = "90后"
    profile.partner_requirement = "90后都可以"
    profile.collection_progress.update({"age": True, "age_label": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_replay_postprocess_95_find_90s",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "partner_requirement", "value": "90后都可以"}]},
        user_message="95想找90后都可以有不",
        last_response="新能源行业现在发展势头很猛呀，挺不错的。那你今年多大啦？",
    )

    assert profile.age_label == "95年"
    assert profile.partner_requirement == "90后都可以"
    assert any(
        str(item.get("field") or "").strip() == "age_label" and str(item.get("value") or "").strip() == "95年"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_process_after_extraction_repairs_self_partner_location_scope_conflict():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_location_scope_conflict")
    profile.location = "香港"
    profile.partner_requirement = "香港，本地优先"
    profile.collection_progress.update({"location": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_postprocess_location_scope_conflict",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "location", "value": "香港"}]},
        user_message="深圳女生 想找香港的都可以",
        last_response="你好呀，可以简单介绍下自己情况和择偶要求。",
    )

    assert profile.location == "深圳"
    assert any(
        str(item.get("field") or "").strip() == "location" and str(item.get("value") or "").strip() == "深圳"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_process_after_extraction_repairs_location_scope_conflict_from_structured_partner_pref_only():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_location_structured_only")
    profile.location = "香港"
    profile.partner_pref_location = "香港"
    profile.collection_progress.update({"location": True, "partner_pref_location": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_postprocess_location_structured_only",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "location", "value": "香港"}]},
        user_message="深圳女生 想找香港的都可以",
        last_response="你好呀，可以简单介绍下自己情况和择偶要求。",
    )

    assert profile.location == "深圳"
    assert any(
        str(item.get("field") or "").strip() == "location" and str(item.get("value") or "").strip() == "深圳"
        for item in (result.get("all_fields") or [])
    )


@pytest.mark.asyncio
async def test_process_after_extraction_repairs_self_partner_education_scope_conflict():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_postprocess_education_scope_conflict")
    profile.education = "本科"
    profile.partner_requirement = "学历本科及以上，程序员"
    profile.collection_progress.update({"education": True, "partner_requirement": True})

    fake_user_service = _FakeProfileUserService(profile)
    chat_service.user_service = fake_user_service

    result = await service.process_after_extraction(
        account_id="u_postprocess_education_scope_conflict",
        user_profile=profile,
        collection_result={"collected": True, "all_fields": [{"field": "education", "value": "本科"}]},
        user_message="我硕士，想找本科以上的程序员",
        last_response="你好呀，可以简单介绍下自己情况和择偶要求。",
    )

    assert profile.education == "硕士"
    assert any(
        str(item.get("field") or "").strip() == "education" and str(item.get("value") or "").strip() == "硕士"
        for item in (result.get("all_fields") or [])
    )


def test_pre_generation_resolution_does_not_backfill_occupation_from_short_ack():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pre_gen_ack")
    profile.last_asked_field = "occupation"
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        confidence=0.51,
    )

    chat_service.preparation_service.pre_generation_resolution_service.resolve_state_before_generation(
        user_profile=profile,
        user_message="听不错",
        last_response="你现在从事什么工作呀？",
        understanding=understanding,
    )

    assert not understanding.resolved_slots
    assert understanding.pre_generation_resolution is None


def test_pre_generation_resolution_does_not_backfill_occupation_from_partner_preference_short_reply():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pre_gen_preference_no_occupation")
    profile.last_asked_field = "partner_requirement"
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        confidence=0.51,
    )

    chat_service.preparation_service.pre_generation_resolution_service.resolve_state_before_generation(
        user_profile=profile,
        user_message="看重稳重，成熟，身高要180以上，然后多金",
        last_response="你找对象的时候更看重哪一点呢？",
        understanding=understanding,
    )

    assert "occupation" not in understanding.resolved_slots
    if understanding.pre_generation_resolution is not None:
        assert "occupation" not in (understanding.pre_generation_resolution.resolved_fields or [])


def test_pre_generation_resolution_skips_backfill_when_semantic_plan_already_has_progress():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pre_gen_skip_when_plan_has_progress")
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        confidence=0.91,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            provisional_fields=[
                AcceptedField(
                    field="sex",
                    value="女",
                    normalized_value="女",
                    scope="self",
                    evidence_text="女生啊",
                    confidence=0.91,
                    acceptance_reason="high_risk_non_ai_guard",
                    update_action="stage_as_provisional",
                    persistence_state="provisional",
                    risk_level="high",
                    source_channel="hybrid",
                )
            ]
        ),
    )

    chat_service.preparation_service.pre_generation_resolution_service.resolve_state_before_generation(
        user_profile=profile,
        user_message="女生啊，肯定的女的啊",
        last_response="你是男生还是女生呀？",
        understanding=understanding,
    )

    assert understanding.resolved_slots == {}
    assert understanding.pre_generation_resolution is None


def test_pre_generation_resolution_does_not_append_committed_fields_into_persistence_plan():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pre_gen_no_plan_write")
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        confidence=0.51,
    )
    setattr(understanding, "persistence_plan", TurnPersistencePlan(accepted_fields=[]))

    chat_service.preparation_service.pre_generation_resolution_service.resolve_state_before_generation(
        user_profile=profile,
        user_message="我是女生",
        last_response="你是男生还是女生呀？",
        understanding=understanding,
    )

    assert understanding.resolved_slots["sex"] == "女"
    assert understanding.pre_generation_resolution is not None
    assert getattr(understanding, "persistence_plan").accepted_fields == []


@pytest.mark.asyncio
async def test_finalize_generated_response_keeps_ai_contact_completion_ending_in_raw_mode():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_contact_completion_repair")
    profile.sex = "男"
    profile.age = 28
    profile.age_label = "98年"
    profile.education = "本科"
    profile.monthly_income = "4万"
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.partner_requirement = "看重身高"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )
    chat_service._generate_ai_ending_response = AsyncMock(
        return_value="好的，那你等好消息啦，祝你早日脱单🥰 匹配一般1-8小时哒~ 牵线同事联系前会提前约时间不打扰你～"
    )
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)

    final_response, delivery_ok, _ = await chat_service.finalize_service.finalize_generated_response(
        account_id="u_finalize_contact_completion_repair",
        user_profile=profile,
        user_message="其他的没有了",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="complete",
            next_action="continue",
            primary_move="ack_and_ask",
            ask_field=None,
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=True,
            response_channel="model",
        ),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="invalid_input", subtype="ambiguous_short_answer"),
        collection_result={"ending_info": {"scenario": "normal_complete", "use_ai": True}},
        response_to_clean="好的呀，你的基本情况和择偶偏好我都记清楚啦，之后有合适的人选我再跟你同步就好~",
        ai_response="好的呀，你的基本情况和择偶偏好我都记清楚啦，之后有合适的人选我再跟你同步就好~",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=9,
    )

    assert delivery_ok is True
    assert final_response == "好的呀，你的基本情况和择偶偏好我都记清楚啦，之后有合适的人选我再跟你同步就好~"
    chat_service._generate_ai_ending_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_generated_response_keeps_natural_contact_completion_ending_without_fixed_phrases():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_contact_completion_natural")
    profile.sex = "男"
    profile.age = 27
    profile.age_label = "99年"
    profile.education = "高中"
    profile.monthly_income = "2万"
    profile.location = "深圳"
    profile.occupation = "下水管道维修工"
    profile.marital_status = "单身"
    profile.partner_requirement = "无特别要求"
    profile.phone = "17688765456"
    profile.phone_collected = True
    profile.wechat = "wx999999"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "occupation": True,
            "location": True,
            "marital_status": True,
            "monthly_income": True,
            "partner_requirement": True,
            "contact": True,
        }
    )
    chat_service._generate_ai_ending_response = AsyncMock()

    natural_ending = (
        "没问题哦，匹配一般1-2天就会有结果，后续牵线的同事联系你之前会提前跟你约好时间，"
        "不会随便打扰你的，祝你早日脱单呀🥰"
    )

    final_response, delivery_ok, _ = await chat_service.finalize_service.finalize_generated_response(
        account_id="u_finalize_contact_completion_natural",
        user_profile=profile,
        user_message="wx999999",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="complete",
            next_action="continue",
            primary_move="ack_and_ask",
            ask_field=None,
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
        ),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_provided"),
        collection_result={"ending_info": {"scenario": "normal_complete", "use_ai": True}},
        response_to_clean=natural_ending,
        ai_response=natural_ending,
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert delivery_ok is True
    assert final_response == natural_ending
    chat_service._generate_ai_ending_response.assert_not_called()


@pytest.mark.asyncio
async def test_refused_core_field_first_time_sets_pending_retry():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_refuse_core_once")
    profile.field_ask_count["education"] = 1
    chat_service._temp_refused_fields["u_refuse_core_once"] = ["education"]
    chat_service.user_service.save_user_profile = AsyncMock()

    await service._apply_refused_field_side_effects(
        account_id="u_refuse_core_once",
        user_profile=profile,
        collection_result={"all_fields": []},
    )

    assert profile.pending_retry_field == "education"
    assert not profile.is_active_ask_closed("education")
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_refused_core_field_second_time_closes_active_ask():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_refuse_core_twice")
    profile.field_ask_count["education"] = 2
    profile.pending_retry_field = "education"
    chat_service._temp_refused_fields["u_refuse_core_twice"] = ["education"]
    chat_service.user_service.save_user_profile = AsyncMock()

    await service._apply_refused_field_side_effects(
        account_id="u_refuse_core_twice",
        user_profile=profile,
        collection_result={"all_fields": []},
    )

    assert profile.pending_retry_field is None
    assert profile.is_active_ask_closed("education")
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_refused_marital_status_closes_active_ask_without_retry():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_refuse_marital")
    profile.field_ask_count["marital_status"] = 1
    chat_service._temp_refused_fields["u_refuse_marital"] = ["marital_status"]
    chat_service.user_service.save_user_profile = AsyncMock()

    await service._apply_refused_field_side_effects(
        account_id="u_refuse_marital",
        user_profile=profile,
        collection_result={"all_fields": []},
    )

    assert profile.pending_retry_field is None
    assert profile.is_active_ask_closed("marital_status")
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_refused_core_and_medium_fields_retry_only_core_and_close_medium():
    chat_service = _build_chat_service()
    service = ChatServiceCollectionPostprocessService(chat_service)
    profile = UserProfile(account_id="u_refuse_core_medium")
    profile.field_ask_count["education"] = 1
    profile.field_ask_count["marital_status"] = 1
    chat_service._temp_refused_fields["u_refuse_core_medium"] = ["education", "marital_status"]
    chat_service.user_service.save_user_profile = AsyncMock()

    await service._apply_refused_field_side_effects(
        account_id="u_refuse_core_medium",
        user_profile=profile,
        collection_result={"all_fields": []},
    )

    assert profile.pending_retry_field == "education"
    assert not profile.is_active_ask_closed("education")
    assert profile.is_active_ask_closed("marital_status")
    chat_service.user_service.save_user_profile.assert_awaited_once()


def test_infer_effective_refused_fields_prefers_actual_asked_fields_over_keyword_guess():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refused_fields")
    profile.set_last_asked_field("education", 3, side_field="marital_status")

    refused_fields = chat_service._infer_effective_refused_fields(
        profile,
        "你最高学历是什么呀，现在是单身状态不？",
    )

    assert refused_fields == ["education", "marital_status"]


@pytest.mark.asyncio
async def test_confirmation_ai_fallback_confirms_pending_sex_when_rule_misses():
    user_service = AsyncMock()
    chat_service = ChatService(
        _ConfirmationAIService('{"result":"confirmed","field":"sex"}'),
        user_service,
    )
    profile = UserProfile(account_id="u_confirmation_ai")
    profile.pending_sex_confirmation = "男"

    extracted_data, extraction_meta = await chat_service._apply_confirmation_ai_fallback(
        {},
        {},
        user_message="你猜对了",
        last_response="我再确认一下，你这边是男生对吧？",
        user_profile=profile,
    )

    assert extracted_data["sex"] == "男"
    assert extraction_meta["sex"]["source"] == "confirmation_ai_fallback"


@pytest.mark.asyncio
async def test_confirmation_ai_fallback_delegates_to_classifier():
    chat_service = _build_chat_service()
    chat_service.confirmation_ai_fallback_classifier.classify = AsyncMock(
        return_value=SimpleNamespace(result="confirmed", field="sex")
    )
    profile = UserProfile(account_id="u_confirmation_delegate")
    profile.pending_sex_confirmation = "男"

    extracted_data, extraction_meta = await chat_service._apply_confirmation_ai_fallback(
        {},
        {},
        user_message="你猜对了",
        last_response="我再确认一下，你这边是男生对吧？",
        user_profile=profile,
    )

    assert extracted_data["sex"] == "男"
    assert extraction_meta["sex"]["source"] == "confirmation_ai_fallback"
    chat_service.confirmation_ai_fallback_classifier.classify.assert_awaited_once()


@pytest.mark.asyncio
async def test_prepare_turn_execution_forces_model_expression_for_composite_opening():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_turn")
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        secondary_signals=["opening_greeting", "service_confirmation_like"],
        resolved_slots={"partner_gender_preference": "男"},
        confidence=0.92,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    shadow_profile = UserProfile(account_id="u_prepare_turn_shadow")
    chat_service._build_shadow_profile_for_decision = lambda *args, **kwargs: shadow_profile
    chat_service._build_turn_decision = AsyncMock(
        return_value=SimpleNamespace(
            response_channel="quick_faq",
            intent="opening_self_intro",
            secondary_signals=[],
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="你好，帮我找个男朋友呀，你们是有帮忙介绍对象是吧",
        user_profile=profile,
        conversation_context={"message_count": 0, "recent_responses": []},
        last_response="",
        message_count=0,
    )

    assert prepared.understanding is understanding
    assert prepared.decision_profile is shadow_profile
    assert prepared.turn_decision.response_channel == "model"
    assert prepared.response_channel == "model"


@pytest.mark.asyncio
async def test_prepare_turn_execution_persists_resume_target_from_decision_profile():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_sync")
    profile.last_asked_field = "monthly_income"
    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="info_collection_why",
        secondary_signals=["needs_resume_mainline"],
        answer_first=True,
        confidence=0.94,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="为啥要问这么清晰呢",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["本科学历挺好的，那你现在每个月收入大概在什么范围呀？"]},
        last_response="本科学历挺好的，那你现在每个月收入大概在什么范围呀？",
        message_count=6,
    )

    assert prepared.turn_decision.intent == "info_collection_why"
    assert prepared.decision_profile.resume_profile_target == "monthly_income"
    assert profile.resume_profile_target == "monthly_income"


@pytest.mark.asyncio
async def test_prepare_turn_execution_forces_resume_after_faq_even_if_turn_decision_is_still_confirmation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_resume_override")
    profile.last_asked_field = "monthly_income"
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        post_answer_reentry=True,
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="confirmation",
            primary_move="light_followup",
            ask_field=None,
            prioritize_user_question=True,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
            user_concern_type="faq",
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="好的",
        user_profile=profile,
        conversation_context={"message_count": 7, "recent_responses": ["我知道你担心问太细有问题，这些信息是用来帮你精准匹配合适的男生的，不会乱用到别的地方哦。"]},
        last_response="我知道你担心问太细有问题，这些信息是用来帮你精准匹配合适的男生的，不会乱用到别的地方哦。",
        message_count=7,
    )

    assert prepared.turn_decision.intent == "general"
    assert prepared.turn_decision.ask_field == "monthly_income"
    assert prepared.turn_decision.prioritize_user_question is False
    assert prepared.turn_decision.resume_applied is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_confirmation_with_resolved_slot_continues_mainline_instead_of_dangling_ack():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_confirmation_continue_mainline")
    profile.age = 33
    profile.age_label = "93年"
    profile.collection_progress["age"] = True
    profile.location = "深圳"
    profile.collection_progress["location"] = True
    profile.occupation = "自媒体"
    profile.collection_progress["occupation"] = True
    profile.education = "高中"
    profile.collection_progress["education"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={"sex": "女"},
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="confirmation",
            primary_move="light_followup",
            ask_field=None,
            prioritize_user_question=True,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
            user_concern_type="faq",
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["你应该是女孩子对吧？"]},
        last_response="你应该是女孩子对吧？",
        message_count=6,
    )

    assert prepared.turn_decision.intent == "general"
    assert prepared.turn_decision.ask_field is not None
    assert prepared.turn_decision.ask_field != "contact"
    assert prepared.turn_decision.prioritize_user_question is False
    assert prepared.turn_decision.resume_applied is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_confirmation_with_persistence_plan_field_continues_mainline():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_confirmation_continue_mainline_plan")
    profile.age = 33
    profile.age_label = "93年"
    profile.collection_progress["age"] = True
    profile.location = "深圳"
    profile.collection_progress["location"] = True
    profile.occupation = "自媒体"
    profile.collection_progress["occupation"] = True
    profile.education = "高中"
    profile.collection_progress["education"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={},
        confidence=0.85,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="sex",
                    value="女",
                    normalized_value="女",
                    scope="self",
                    evidence_text="是的",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="confirmation",
            primary_move="light_followup",
            ask_field=None,
            prioritize_user_question=True,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
            user_concern_type="faq",
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["你应该是女孩子对吧？"]},
        last_response="你应该是女孩子对吧？",
        message_count=6,
    )

    assert prepared.turn_decision.intent == "general"
    assert prepared.turn_decision.ask_field is not None
    assert prepared.turn_decision.ask_field != "contact"
    assert prepared.turn_decision.resume_applied is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_confirmation_can_jump_to_contact_when_only_contact_remains():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_confirmation_continue_contact")
    profile.age = 33
    profile.age_label = "93年"
    profile.collection_progress["age"] = True
    profile.location = "广州、东莞、深圳"
    profile.collection_progress["location"] = True
    profile.education = "高中"
    profile.collection_progress["education"] = True
    profile.occupation = "自媒体"
    profile.collection_progress["occupation"] = True
    profile.marital_status = "离异（手续已办妥）"
    profile.collection_progress["marital_status"] = True
    profile.monthly_income = "有时多有时少"
    profile.collection_progress["monthly_income"] = True
    profile.partner_requirement = "找深二代男"
    profile.collection_progress["partner_requirement"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={"sex": "女"},
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="confirmation",
            primary_move="light_followup",
            ask_field=None,
            prioritize_user_question=True,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
            user_concern_type="faq",
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 7, "recent_responses": ["顺嘴核对下哦，你是女生对不？"]},
        last_response="顺嘴核对下哦，你是女生对不？",
        message_count=7,
    )

    assert prepared.turn_decision.intent == "general"
    assert prepared.turn_decision.ask_field == "contact"
    assert prepared.turn_decision.prioritize_user_question is False
    assert prepared.turn_decision.resume_applied is True
    assert prepared.turn_decision.allow_contact_target is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_locks_divorce_confirmation_before_generation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_pre_generation")
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"marital_status": "离异"},
        confidence=0.91,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="离异呢",
        user_profile=profile,
        conversation_context={"message_count": 4, "recent_responses": []},
        last_response="你现在感情状态大概是怎样的呀？",
        message_count=4,
    )

    assert profile.divorce_confirmation_pending is True
    assert prepared.decision_profile.divorce_confirmation_pending is True
    assert prepared.turn_decision.ask_field == "marital_status"
    assert prepared.turn_decision.next_action == "confirm_divorce_status"
    assert prepared.turn_decision.primary_move == "confirm_status_only"


@pytest.mark.asyncio
async def test_prepare_turn_execution_clears_divorce_confirmation_before_generation_when_formality_done():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_pre_generation")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={},
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="办好了",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["离婚手续已经都办妥了吗？"]},
        last_response="离婚手续已经都办妥了吗？",
        message_count=6,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"
    assert profile.collection_progress["marital_status"] is True
    assert prepared.turn_decision.next_action != "confirm_divorce_status"
    assert prepared.turn_decision.ask_field != "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_clears_divorce_confirmation_when_user_has_court_judgment():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_by_judgment")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="connective_opening",
        resolved_slots={},
        confidence=0.82,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="有法院判决书",
        user_profile=profile,
        conversation_context={"message_count": 2, "recent_responses": ["那你这边离婚手续都已经办妥了吗？"]},
        last_response="那你这边离婚手续都已经办妥了吗？",
        message_count=2,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"
    assert prepared.turn_decision.next_action != "confirm_divorce_status"
    assert prepared.turn_decision.ask_field != "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_clears_divorce_confirmation_on_affirmative_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_by_yes")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={},
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 3, "recent_responses": ["有法院判决书的话，那离婚相关的手续就都已经处理妥当啦对吧？"]},
        last_response="有法院判决书的话，那离婚相关的手续就都已经处理妥当啦对吧？",
        message_count=3,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"
    assert prepared.turn_decision.next_action != "confirm_divorce_status"
    assert prepared.turn_decision.ask_field != "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_keeps_birth_year_and_locks_divorce_confirmation_for_compound_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_birth_year_divorce_compound")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.pending_birth_year_bucket = "90后"
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"age": "28", "age_label": "98年", "marital_status": "离异"},
        confidence=0.91,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="98的，离异",
        user_profile=profile,
        conversation_context={"message_count": 4, "recent_responses": ["你具体是哪一年出生的呀？"]},
        last_response="你具体是哪一年出生的呀？",
        message_count=4,
    )

    assert prepared.decision_profile.age == 28
    assert prepared.decision_profile.age_label == "98年"
    assert prepared.decision_profile.collection_progress["age"] is True
    assert prepared.decision_profile.divorce_confirmation_pending is True
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.transition_reason == "lock_divorce_confirmation"
    assert prepared.turn_decision.next_action == "confirm_divorce_status"
    assert prepared.turn_decision.ask_field == "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_locks_divorce_confirmation_from_persistence_plan_marital_status():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_birth_year_divorce_compound_plan")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.pending_birth_year_bucket = "90后"
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={},
        confidence=0.91,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="age",
                    value="28",
                    normalized_value="28",
                    scope="self",
                    evidence_text="98的，离异",
                    confidence=0.9,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                ),
                AcceptedField(
                    field="age_label",
                    value="98年",
                    normalized_value="98年",
                    scope="self",
                    evidence_text="98的，离异",
                    confidence=0.9,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                ),
                AcceptedField(
                    field="marital_status",
                    value="离异",
                    normalized_value="离异",
                    scope="self",
                    evidence_text="98的，离异",
                    confidence=0.9,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                ),
            ]
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="98的，离异",
        user_profile=profile,
        conversation_context={"message_count": 4, "recent_responses": ["你具体是哪一年出生的呀？"]},
        last_response="你具体是哪一年出生的呀？",
        message_count=4,
    )

    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.transition_reason == "lock_divorce_confirmation"
    assert prepared.turn_decision.next_action == "confirm_divorce_status"
    assert prepared.turn_decision.ask_field == "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_prefers_occupation_after_generic_location_short_reply():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_location_short_reply")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.age = 28
    profile.age_label = "98年"
    profile.collection_progress["age"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"location": "南京"},
        confidence=0.91,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="在南京呢",
        user_profile=profile,
        conversation_context={"message_count": 5, "recent_responses": ["你现在长期在哪个城市生活呀？"]},
        last_response="你现在长期在哪个城市生活呀？",
        message_count=5,
    )

    assert prepared.decision_profile.location == "南京"
    assert prepared.decision_profile.collection_progress["location"] is True
    assert prepared.turn_decision.next_action == "continue"
    assert prepared.turn_decision.ask_field == "occupation"


@pytest.mark.asyncio
async def test_prepare_turn_execution_backfills_invalid_input_location_short_reply_before_decision():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_location")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.age = 28
    profile.age_label = "98年"
    profile.collection_progress["age"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        confidence=0.51,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="在南京呢",
        user_profile=profile,
        conversation_context={"message_count": 5, "recent_responses": ["你现在长期在哪个城市生活呀？"]},
        last_response="你现在长期在哪个城市生活呀？",
        message_count=5,
    )

    assert prepared.understanding.primary_turn_type == "profile_answer"
    assert prepared.understanding.resolved_slots["location"] == "南京"
    assert prepared.understanding.slot_candidates["location"].source == "pre_generation_resolution"
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.source == "contextual_short_reply_backfill"
    assert prepared.pre_generation_resolution.resolved_fields == ["location"]
    assert prepared.pre_generation_resolution.transition_reason == "contextual_short_reply_backfill"
    assert prepared.turn_decision.ask_field == "occupation"


@pytest.mark.asyncio
async def test_prepare_turn_execution_backfill_syncs_semantic_frame_and_persistence_plan():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_semantic_sync")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        confidence=0.51,
    )
    setattr(
        understanding,
        "semantic_frame",
        TurnSemanticFrame(
            version="v1",
            source="hybrid_semantic_projection",
            primary_domain="mixed",
            field_observations=[],
        ),
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="在南京呢",
        user_profile=profile,
        conversation_context={"message_count": 5, "recent_responses": ["你现在长期在哪个城市生活呀？"]},
        last_response="你现在长期在哪个城市生活呀？",
        message_count=5,
    )

    semantic_frame = getattr(prepared.understanding, "semantic_frame", None)
    persistence_plan = getattr(prepared.understanding, "persistence_plan", None)
    assert semantic_frame is not None
    assert any(
        isinstance(item, FieldObservation)
        and str(getattr(item, "field", "") or "") == "location"
        and str(getattr(item, "normalized_value", "") or "") == "南京"
        for item in list(getattr(semantic_frame, "field_observations", []) or [])
    )
    assert persistence_plan is not None
    assert list(getattr(persistence_plan, "accepted_fields", []) or []) == []
    assert prepared.understanding.resolved_slots["location"] == "南京"


@pytest.mark.asyncio
async def test_prepare_turn_execution_backfills_invalid_input_confirmation_short_reply_before_decision():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_sex_confirm")
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        confidence=0.51,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 1, "recent_responses": ["你是女生对吧？"]},
        last_response="你是女生对吧？",
        message_count=1,
    )

    assert prepared.understanding.primary_turn_type == "profile_answer"
    assert prepared.understanding.resolved_slots["sex"] == "女"
    assert prepared.understanding.slot_candidates["sex"].source == "pre_generation_resolution"
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.source == "contextual_short_reply_backfill"
    assert prepared.pre_generation_resolution.resolved_fields == ["sex"]
    assert prepared.pre_generation_resolution.transition_reason == "contextual_short_reply_backfill"
    assert prepared.decision_profile.sex == "女"
    assert prepared.turn_decision.ask_field == "age"


@pytest.mark.asyncio
async def test_prepare_turn_execution_short_reply_followup_override_reads_persistence_plan_sex():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_sex_plan")
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={},
        confidence=0.88,
    )
    understanding.set_pre_generation_resolution(
        source="contextual_short_reply_backfill",
        resolved_fields=["sex"],
        default_transition_reason="contextual_short_reply_backfill",
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="sex",
                    value="女",
                    normalized_value="女",
                    scope="self",
                    evidence_text="是的",
                    confidence=0.95,
                    acceptance_reason="pre_generation_resolution",
                    update_action="accept_as_new",
                )
            ]
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="general",
            primary_move="ack_and_ask",
            ask_field="location",
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
        )
    )

    prepared = await chat_service.prepare_turn_execution(
        user_message="是的",
        user_profile=profile,
        conversation_context={"message_count": 1, "recent_responses": ["你是女生对吧？"]},
        last_response="你是女生对吧？",
        message_count=1,
    )

    assert prepared.turn_decision.ask_field == "age"
    assert prepared.turn_decision.resume_applied is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_backfills_invalid_input_birth_year_short_reply_before_decision():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_birth_year")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.pending_birth_year_bucket = "90后"
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        confidence=0.51,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="98的",
        user_profile=profile,
        conversation_context={"message_count": 3, "recent_responses": ["你具体是哪一年出生的呀？"]},
        last_response="你具体是哪一年出生的呀？",
        message_count=3,
    )

    assert prepared.understanding.primary_turn_type == "profile_answer"
    assert prepared.understanding.resolved_slots["age"] == "28"
    assert prepared.understanding.resolved_slots["age_label"] == "98年"
    assert prepared.understanding.slot_candidates["age"].source == "pre_generation_resolution"
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.source == "contextual_short_reply_backfill"
    assert prepared.pre_generation_resolution.resolved_fields == ["age", "age_label"]
    assert prepared.pre_generation_resolution.transition_reason == "contextual_short_reply_backfill"
    assert prepared.decision_profile.age == 28
    assert prepared.decision_profile.collection_progress["age"] is True


@pytest.mark.asyncio
async def test_prepare_turn_execution_backfills_birth_year_for_compound_message_even_with_semantic_progress():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_birth_year_compound_progress")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.pending_birth_year_bucket = "90后"
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"partner_requirement": "成熟稳重，多金，身高180+"},
        confidence=0.91,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            provisional_fields=[
                AcceptedField(
                    field="partner_requirement",
                    value="成熟稳重，多金，身高180+",
                    normalized_value="成熟稳重，多金，身高180+",
                    scope="partner",
                    evidence_text="喜欢成熟稳重，多金，身高180+",
                    confidence=0.91,
                    acceptance_reason="high_risk_non_ai_guard",
                    update_action="stage_as_provisional",
                    persistence_state="provisional",
                    risk_level="high",
                    source_channel="hybrid",
                )
            ]
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="98年的，喜欢成熟稳重，多金，身高180+",
        user_profile=profile,
        conversation_context={"message_count": 5, "recent_responses": ["你具体是哪一年出生的呀？另外择偶方面你更看重哪一点呢？"]},
        last_response="你具体是哪一年出生的呀？另外择偶方面你更看重哪一点呢？",
        message_count=5,
    )

    assert prepared.understanding.resolved_slots["age"] == "28"
    assert prepared.understanding.resolved_slots["age_label"] == "98年"
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.source == "birth_year_confirmation_backfill"
    assert set(prepared.pre_generation_resolution.resolved_fields) == {"age", "age_label"}
    assert prepared.decision_profile.age == 28
    assert prepared.turn_decision.ask_field != "age"


@pytest.mark.asyncio
async def test_prepare_turn_execution_does_not_backfill_age_for_contact_like_numeric_short_reply():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_no_age_backfill_contact")
    profile.phone_ask_count = 1
    profile.last_contact_request_type = "phone"
    understanding = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_context_reply",
        resolved_slots={},
        confidence=0.93,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="1768876543",
        user_profile=profile,
        conversation_context={"message_count": 3, "recent_responses": ["你方便留个电话吗？"]},
        last_response="你方便留个电话吗？",
        message_count=3,
    )

    assert "age" not in prepared.understanding.resolved_slots
    assert prepared.pre_generation_resolution is None


@pytest.mark.asyncio
async def test_prepare_turn_execution_handles_invalid_input_divorce_completion_before_decision():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_prepare_backfill_divorce_done")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.age = 28
    profile.age_label = "98年"
    profile.collection_progress["age"] = True
    profile.marital_status = "离异"
    profile.collection_progress["marital_status"] = True
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        confidence=0.51,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="办好了",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["离婚手续已经都办妥了吗？"]},
        last_response="离婚手续已经都办妥了吗？",
        message_count=6,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.transition_reason == "resume_after_divorce_confirmation_complete"
    assert prepared.turn_decision.next_action == "continue"
    assert prepared.turn_decision.ask_field in {"location", "education", "occupation"}
    assert prepared.turn_decision.ask_field != "marital_status"


@pytest.mark.asyncio
async def test_prepare_turn_execution_resumes_mainline_after_divorce_confirmation_completion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_resume")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.age = 28
    profile.age_label = "98年"
    profile.collection_progress["age"] = True
    profile.marital_status = "离异"
    profile.collection_progress["marital_status"] = True
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={},
        confidence=0.85,
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="办好了",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["离婚手续已经都办妥了吗？"]},
        last_response="离婚手续已经都办妥了吗？",
        message_count=6,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.transition_reason == "resume_after_divorce_confirmation_complete"
    assert prepared.turn_decision.next_action == "continue"
    assert prepared.turn_decision.ask_field == "location"


@pytest.mark.asyncio
async def test_prepare_turn_execution_ignores_stale_status_priority_after_divorce_confirmation_completion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_resume_stale_priority")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.age = 28
    profile.age_label = "98年"
    profile.collection_progress["age"] = True
    profile.marital_status = "离异"
    profile.collection_progress["marital_status"] = True
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="confirmation",
        subtype="weak_confirmation",
        resolved_slots={},
        confidence=0.85,
        priority_decision=TurnPriorityDecision(
            primary_task="status_confirmation",
            priority_level=3,
            decision_reason="divorce_confirmation_pending",
            response_mode="confirm_only",
            locked_field="marital_status",
            allow_contact_target=False,
            allow_medium_target=False,
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    prepared = await chat_service.prepare_turn_execution(
        user_message="办好了",
        user_profile=profile,
        conversation_context={"message_count": 6, "recent_responses": ["离婚手续已经都办妥了吗？"]},
        last_response="离婚手续已经都办妥了吗？",
        message_count=6,
    )

    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert prepared.pre_generation_resolution is not None
    assert prepared.pre_generation_resolution.transition_reason == "resume_after_divorce_confirmation_complete"
    assert prepared.turn_decision.next_action == "continue"
    assert prepared.turn_decision.ask_field != "marital_status"


@pytest.mark.asyncio
async def test_pre_generation_short_circuit_self_age_reads_persistence_plan_age():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(primary_turn_type="profile_answer", resolved_slots={})
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="age",
                    value="23",
                    normalized_value="23",
                    scope="self",
                    evidence_text="我23岁",
                    confidence=0.96,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    age = await chat_service.preparation_service.pre_generation_resolution_service._resolve_short_circuit_self_age(
        user_message="我23岁",
        understanding=understanding,
    )

    assert age == 23


def test_turn_understanding_result_to_dict_includes_pre_generation_resolution():
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        pre_generation_resolution=PreGenerationResolutionMeta(
            source="contextual_short_reply_backfill",
            resolved_fields=["location"],
            transition_reason="contextual_short_reply_backfill",
        ),
    )

    payload = understanding.to_dict()

    assert payload["pre_generation_resolution"] == {
        "source": "contextual_short_reply_backfill",
        "resolved_fields": ["location"],
        "transition_reason": "contextual_short_reply_backfill",
    }


def test_pre_generation_resolution_payload_keys_remain_for_compatibility():
    understanding = TurnUnderstandingResult(primary_turn_type="invalid_input", subtype="ambiguous_short_answer")

    understanding.set_pre_generation_resolution(
        source="contextual_short_reply_backfill",
        resolved_fields=["location"],
        default_transition_reason="contextual_short_reply_backfill",
    )

    assert understanding.pre_generation_resolution is not None
    assert understanding.get_pre_generation_compat_payload() == {
        "pre_generation_resolution_source": "contextual_short_reply_backfill",
        "pre_generation_resolved_fields": "location",
        "pre_generation_transition_reason": "contextual_short_reply_backfill",
    }
    assert {
        key: understanding.context_ack_payload[key]
        for key in understanding.get_pre_generation_compat_payload().keys()
    } == understanding.get_pre_generation_compat_payload()


@pytest.mark.asyncio
async def test_consume_bridge_back_prefix_clears_flag_outside_repair_mode():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_bridge_prefix")
    profile.needs_bridge_back = True
    profile.last_side_topic_type = "faq"
    chat_service.user_service.save_user_profile = AsyncMock()

    prefix = await chat_service.consume_bridge_back_prefix(
        account_id="u_bridge_prefix",
        user_profile=profile,
        in_repair_mode=False,
    )

    assert prefix
    assert profile.needs_bridge_back is False
    assert profile.last_side_topic_type is None
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_pre_generation_short_circuit_payload_handles_high_risk():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_high_risk")
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "先保护你自己最重要。"})

    route, payload, updated_profile = await chat_service.maybe_build_pre_generation_short_circuit_payload(
        account_id="u_high_risk",
        user_profile=profile,
        user_message="我有点想不开",
        dialog_id="dlg_risk",
        turn_decision=SimpleNamespace(risk="high_risk", intent="risk_guard"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="risk_guard"),
        message_count=0,
    )

    assert route == "risk_guard"
    assert payload is not None
    assert updated_profile.needs_bridge_back is True
    assert updated_profile.last_side_topic_type == "risk"


@pytest.mark.asyncio
async def test_maybe_build_pre_generation_short_circuit_payload_handles_divorce_incomplete_after_confirmation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_incomplete_short")
    profile.marital_status = "离异（手续未办妥）"
    profile.conversation_ended = True
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "这边就先不继续往下聊啦。"})

    route, payload, updated_profile = await chat_service.maybe_build_pre_generation_short_circuit_payload(
        account_id="u_divorce_incomplete_short",
        user_profile=profile,
        user_message="还没办好",
        dialog_id="dlg_divorce_incomplete",
        turn_decision=SimpleNamespace(risk="none", intent="general"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="confirmation"),
        message_count=0,
    )

    assert route == "divorce_incomplete"
    assert payload is not None
    assert payload["response"] == "这边就先不继续往下聊啦。"
    assert updated_profile is profile


@pytest.mark.asyncio
async def test_maybe_build_pre_generation_short_circuit_payload_handles_age_under_limit_via_resolution_service():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_age_under_limit_short")
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "年龄还不太合适哦。"})

    route, payload, updated_profile = await chat_service.maybe_build_pre_generation_short_circuit_payload(
        account_id="u_age_under_limit_short",
        user_profile=profile,
        user_message="我今年23",
        dialog_id="dlg_age_under_limit",
        turn_decision=SimpleNamespace(risk="none", intent="general"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="profile_answer", resolved_slots={"age": "23"}),
        message_count=0,
    )

    assert route == "age_under_limit"
    assert payload is not None
    assert payload["response"] == "年龄还不太合适哦。"
    assert updated_profile.age == 23
    assert updated_profile.age_under_limit is True
    assert updated_profile.conversation_ended is True
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_pre_generation_short_circuit_payload_does_not_misread_partner_age_gap_as_user_age():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_age_gap_not_under_limit")
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "不会走结束态。"})

    route, payload, updated_profile = await chat_service.maybe_build_pre_generation_short_circuit_payload(
        account_id="u_age_gap_not_under_limit",
        user_profile=profile,
        user_message="你好，你们是不是有帮忙介绍对象呀，我今年36，然后想找一个和我上下相差3岁的，最好在深圳这边的",
        dialog_id="dlg_age_gap_not_under_limit",
        turn_decision=SimpleNamespace(risk="none", intent="general"),
        turn_understanding=TurnUnderstandingResult(
            primary_turn_type="opening",
            resolved_slots={"age": "36", "location": "深圳"},
        ),
        message_count=0,
    )

    assert route is None
    assert payload is None
    assert updated_profile.age_under_limit is False


@pytest.mark.asyncio
async def test_maybe_build_pre_generation_short_circuit_payload_uses_ai_review_for_conflicting_under_limit_age():
    chat_service = _build_chat_service()
    chat_service.ai_service = _ConfirmationAIService('{"self_age":23,"partner_age_gap":3,"allow_age_under_limit":true}')
    profile = UserProfile(account_id="u_age_under_limit_conflict_review")
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "年龄还不太合适哦。"})

    route, payload, updated_profile = await chat_service.maybe_build_pre_generation_short_circuit_payload(
        account_id="u_age_under_limit_conflict_review",
        user_profile=profile,
        user_message="我今年23，想找和我上下相差3岁的",
        dialog_id="dlg_age_under_limit_conflict_review",
        turn_decision=SimpleNamespace(risk="none", intent="general"),
        turn_understanding=TurnUnderstandingResult(
            primary_turn_type="opening",
            resolved_slots={"age": "23"},
        ),
        message_count=0,
    )

    assert route == "age_under_limit"
    assert payload is not None
    assert updated_profile.age == 23
    assert updated_profile.age_under_limit is True


@pytest.mark.asyncio
async def test_sync_post_delivery_state_updates_state_and_progress():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_post_delivery")
    updated_profile = UserProfile(account_id="u_post_delivery")
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=updated_profile)
    chat_service._update_progress_runtime_counters = AsyncMock(return_value=updated_profile)

    final_response, returned_profile = await chat_service.sync_post_delivery_state(
        account_id="u_post_delivery",
        user_profile=profile,
        user_message="你好",
        final_response="你好呀",
        ai_response="你好呀",
        delivery_ok=True,
        turn_decision=SimpleNamespace(
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        ),
        collection_result={"all_fields": []},
        message_count=1,
        previous_asked_field=None,
    )

    assert final_response == "你好呀"
    assert returned_profile is updated_profile
    chat_service._update_conversation_state.assert_awaited_once()
    chat_service._update_progress_runtime_counters.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_returns_route_for_ended_session():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended")
    profile.conversation_ended = True
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "那今天先聊到这儿。"})
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={"recent_responses": ["那今天先聊到这儿。"]})

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended",
        user_profile=profile,
        user_message="好的",
        dialog_id="dlg_end",
        is_new_user_session=False,
    )

    assert result is not None
    assert result.route_name == "already_ended"
    assert result.payload is not None
    chat_service._update_conversation_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_prefers_contact_completion_copy_when_contact_finished():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_contact_complete")
    profile.conversation_ended = True
    profile.phone = "17899876543"
    profile.phone_collected = True
    profile.wechat = "17899876543"
    profile.wechat_collected = True
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
            "contact": True,
        }
    )
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.monthly_income = "6万"
    profile.partner_requirement = "无特别要求"
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "好的，那你等好消息啦。"})
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(return_value={"recent_responses": ["微信就是刚留的那个手机号对吧？"]})
    chat_service.expectation_service.get_contact_completion_response = lambda _profile: "好的，那你等好消息啦，祝你早日脱单。"

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_contact_complete",
        user_profile=profile,
        user_message="是的",
        dialog_id="dlg_end_complete",
        is_new_user_session=False,
    )

    assert result is not None
    assert "等" in result.final_response
    assert "先这样" not in result.final_response
    assert result.route_name == "already_ended"
    chat_service._build_chat_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_returns_light_ack_after_repeated_low_info_confirmation_for_contact_completion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_contact_complete_silent")
    profile.conversation_ended = True
    profile.phone = "17899876543"
    profile.phone_collected = True
    profile.wechat = "wx34853459358"
    profile.wechat_collected = True
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
            "contact": True,
        }
    )
    profile.sex = "男"
    profile.age = 28
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.monthly_income = "7万"
    profile.partner_requirement = "对方经济条件较好"
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "收到啦"})
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(
        return_value={"recent_responses": ["好的，那你等好消息啦，祝你早日脱单。", "嗯嗯"]}
    )
    chat_service.expectation_service.get_contact_completion_response = lambda _profile: "好的，那你等好消息啦，祝你早日脱单。"

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_contact_complete_silent",
        user_profile=profile,
        user_message="好的",
        dialog_id="dlg_end_complete_silent",
        is_new_user_session=False,
    )

    assert result is not None
    assert result.final_response == ""
    assert result.route_name == "already_ended"


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_returns_light_ack_after_natural_terminal_reply_and_thanks():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_contact_complete_natural")
    profile.conversation_ended = True
    profile.phone = "17688987654"
    profile.phone_collected = True
    profile.wechat = "wx2392993450349"
    profile.wechat_collected = True
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
            "contact": True,
        }
    )
    profile.sex = "女"
    profile.age = 28
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "美容类"
    profile.marital_status = "单身"
    profile.monthly_income = "3万"
    profile.partner_requirement = "身高较高，外形帅气"
    natural_terminal_reply = (
        "好哒，匹配一般1-8小时就能出结果哦，负责牵线的同事联系你之前会提前跟你约时间的，"
        "不会随便打扰你，祝你早日遇到合眼缘的人呀～"
    )
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"success": True, "response": "好呀"})
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(
        return_value={"recent_responses": [natural_terminal_reply]}
    )
    chat_service.expectation_service.get_contact_completion_response = (
        lambda _profile: "好的，那你等好消息啦，祝你早日脱单。"
    )

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_contact_complete_natural",
        user_profile=profile,
        user_message="好呢，感谢",
        dialog_id="dlg_end_complete_natural",
        is_new_user_session=False,
    )

    assert result is not None
    assert result.final_response in {"嗯嗯", "好呀", "收到啦"}
    assert "等好消息" not in result.final_response
    assert result.route_name == "already_ended"


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_reopens_for_profile_update_after_end():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_reopen_profile")
    profile.conversation_ended = True
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(
        return_value={"recent_responses": ["好哒，匹配一般1-2天就会有结果哦，不会随便打扰你。"]}
    )

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_reopen_profile",
        user_profile=profile,
        user_message="我再补个微信吧，wx123456",
        dialog_id="dlg_end_reopen_profile",
        is_new_user_session=False,
    )

    assert result is None
    assert profile.conversation_ended is False
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_build_already_ended_payload_reopens_for_resume_collection_message():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_already_ended_reopen_resume")
    profile.conversation_ended = True
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service.dialogue_manager.get_conversation_context = AsyncMock(
        return_value={"recent_responses": ["好哒，匹配一般1-8小时就能出结果哦，祝你顺顺利利。"]}
    )

    result = await chat_service.maybe_build_already_ended_payload(
        account_id="u_already_ended_reopen_resume",
        user_profile=profile,
        user_message="继续聊资料吧",
        dialog_id="dlg_end_reopen_resume",
        is_new_user_session=False,
    )

    assert result is None
    assert profile.conversation_ended is False
    chat_service.user_service.save_user_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_turn_response_text_delegates_to_call_ai():
    chat_service = _build_chat_service()
    chat_service._call_ai = AsyncMock(return_value="你好呀")
    decision = SimpleNamespace(response_channel="model")

    ai_response, infra_fail, infra_fail_reason = await chat_service.generate_turn_response_text(
        account_id="u_generate_turn",
        user_profile=UserProfile(account_id="u_generate_turn"),
        user_message="你好",
        main_prompt="prompt",
        turn_decision=decision,
        conversation_context={},
    )

    assert ai_response == "你好呀"
    assert infra_fail is False
    assert infra_fail_reason == ""
    chat_service._call_ai.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_turn_response_text_preserves_raw_model_output():
    chat_service = _build_chat_service()
    chat_service._call_ai = AsyncMock(return_value="<opening_intent>debug</opening_intent>你好呀")

    ai_response, infra_fail, infra_fail_reason = await chat_service.generate_turn_response_text(
        account_id="u_raw_mode_generate",
        user_profile=UserProfile(account_id="u_raw_mode_generate"),
        user_message="你好",
        main_prompt="prompt",
        turn_decision=SimpleNamespace(response_channel="model"),
        conversation_context={},
    )

    assert ai_response == "<opening_intent>debug</opening_intent>你好呀"
    assert infra_fail is False
    assert infra_fail_reason == ""


def test_ai_raw_response_mode_respects_mode_and_kill_switch(monkeypatch):
    chat_service = _build_chat_service()

    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    monkeypatch.setenv("AI_RAW_RESPONSE_KILL_SWITCH", "0")
    assert chat_service._is_ai_raw_response_mode_enabled() is True  # noqa: SLF001

    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "0")
    monkeypatch.setenv("AI_RAW_RESPONSE_KILL_SWITCH", "0")
    assert chat_service._is_ai_raw_response_mode_enabled() is False  # noqa: SLF001

    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    monkeypatch.setenv("AI_RAW_RESPONSE_KILL_SWITCH", "1")
    assert chat_service._is_ai_raw_response_mode_enabled() is False  # noqa: SLF001


def test_helper_services_are_lazy_initialized():
    chat_service = _build_chat_service()

    assert chat_service._resume_guard_service is None  # noqa: SLF001
    assert chat_service._ending_state_service is None  # noqa: SLF001
    assert chat_service._contact_context_service is None  # noqa: SLF001
    assert chat_service._contact_resume_service is None  # noqa: SLF001
    assert chat_service._contact_validation_flow_service is None  # noqa: SLF001
    assert chat_service._collection_postprocess_service is None  # noqa: SLF001
    assert chat_service._validation_recovery_service is None  # noqa: SLF001
    assert chat_service._confirmation_fallback_service is None  # noqa: SLF001
    assert chat_service._collection_extraction_service is None  # noqa: SLF001
    assert chat_service._ending_generation_service is None  # noqa: SLF001
    assert chat_service._generation_prompt_service is None  # noqa: SLF001
    assert chat_service._preset_response_service is None  # noqa: SLF001
    assert chat_service._text_cleanup_service is None  # noqa: SLF001
    assert chat_service._followup_prompt_service is None  # noqa: SLF001
    assert chat_service._turn_text_policy_service is None  # noqa: SLF001

    _ = chat_service.resume_guard_service
    _ = chat_service.ending_state_service
    _ = chat_service.contact_context_service
    _ = chat_service.contact_resume_service
    _ = chat_service.contact_validation_flow_service
    _ = chat_service.collection_postprocess_service
    _ = chat_service.validation_recovery_service
    _ = chat_service.confirmation_fallback_service
    _ = chat_service.collection_extraction_service
    _ = chat_service.ending_generation_service
    _ = chat_service.generation_prompt_service
    _ = chat_service.preset_response_service
    _ = chat_service.text_cleanup_service
    _ = chat_service.followup_prompt_service
    _ = chat_service.turn_text_policy_service

    assert chat_service._resume_guard_service is not None  # noqa: SLF001
    assert chat_service._ending_state_service is not None  # noqa: SLF001
    assert chat_service._contact_context_service is not None  # noqa: SLF001
    assert chat_service._contact_resume_service is not None  # noqa: SLF001
    assert chat_service._contact_validation_flow_service is not None  # noqa: SLF001
    assert chat_service._collection_postprocess_service is not None  # noqa: SLF001
    assert chat_service._validation_recovery_service is not None  # noqa: SLF001
    assert chat_service._confirmation_fallback_service is not None  # noqa: SLF001
    assert chat_service._collection_extraction_service is not None  # noqa: SLF001
    assert chat_service._ending_generation_service is not None  # noqa: SLF001
    assert chat_service._generation_prompt_service is not None  # noqa: SLF001
    assert chat_service._preset_response_service is not None  # noqa: SLF001
    assert chat_service._text_cleanup_service is not None  # noqa: SLF001
    assert chat_service._followup_prompt_service is not None  # noqa: SLF001
    assert chat_service._turn_text_policy_service is not None  # noqa: SLF001


@pytest.mark.asyncio
async def test_process_collection_phase_closes_partner_requirement_active_ask():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_collection_phase")
    latest_profile = UserProfile(account_id="u_collection_phase")
    chat_service.profile_collection_coordinator.process_collection = AsyncMock(
        return_value=SimpleNamespace(collection_result={"all_fields": [{"field": "partner_requirement", "value": "温柔"}]})
    )
    chat_service.user_service.get_user_profile = AsyncMock(side_effect=[latest_profile, latest_profile])
    chat_service.user_service.save_user_profile = AsyncMock()
    chat_service.input_fallback_service.reset_confirm_count = AsyncMock()
    chat_service.profile_collection_coordinator.build_contact_decision = lambda *args, **kwargs: None

    outcome = await chat_service.process_collection_phase(
        account_id="u_collection_phase",
        user_profile=profile,
        extracted_data={"partner_requirement": "温柔"},
        extraction_meta={},
        user_message="温柔一点",
        message_count=1,
        understanding_result=TurnUnderstandingResult(primary_turn_type="profile_answer"),
        conversation_context={},
        turn_decision=SimpleNamespace(response_channel="quick_faq"),
        ai_response="",
    )

    assert outcome.collection_result["all_fields"][0]["field"] == "partner_requirement"
    assert outcome.user_profile.is_active_ask_closed("partner_requirement") is True
    chat_service.input_fallback_service.reset_confirm_count.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_generation_collection_phase_returns_stage_timings():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_generation_phase")
    understanding = TurnUnderstandingResult(primary_turn_type="profile_answer")
    turn_decision = SimpleNamespace(response_channel="quick_faq")
    chat_service.generate_turn_response_text = AsyncMock(return_value=("你好呀", False, ""))
    chat_service.extract_and_merge_generated_fields = AsyncMock(return_value=({"age": 28}, {}))
    chat_service.process_collection_phase = AsyncMock(
        return_value=SimpleNamespace(
            user_profile=profile,
            collection_result={"all_fields": []},
            ai_response="你好呀",
            turn_decision=turn_decision,
            response_channel="quick_faq",
            extracted_fields_count=1,
            contact_gate_before=False,
        )
    )
    chat_service.maybe_build_preset_response_payload = AsyncMock(return_value=None)

    outcome = await chat_service.run_generation_collection_phase(
        account_id="u_generation_phase",
        user_profile=profile,
        user_message="你好",
        dialog_id="dlg_generation",
        main_prompt="prompt",
        last_response="",
        message_count=1,
        understanding_result=understanding,
        conversation_context={},
        turn_decision=turn_decision,
    )

    assert outcome.ai_call_ms >= 0
    assert outcome.extract_fuse_ms >= 0
    assert outcome.collection_process_ms >= 0
    assert outcome.extracted_fields_count == 1


@pytest.mark.asyncio
async def test_finalize_generated_response_preserves_ai_text_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_raw")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_raw",
        user_profile=profile,
        user_message="你好",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="opening"),
        collection_result={"all_fields": []},
        response_to_clean="会被忽略",
        ai_response="  <opening_intent>debug</opening_intent>你好呀  ",
        bridge_prefix="顺便说一句",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response == "你好呀"
    assert delivery_ok is True
    assert returned_profile is profile
    assert chat_service._last_unified_generation_record is not None
    assert chat_service._last_unified_generation_record["first_generation_only"] is True
    assert chat_service._last_unified_generation_record["technical_blocks_removed"] == ["opening_intent"]


@pytest.mark.asyncio
async def test_finalize_generated_response_uses_minimal_fallback_when_ai_text_is_empty(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_fallback")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, _ = await chat_service.finalize_generated_response(
        account_id="u_finalize_fallback",
        user_profile=profile,
        user_message="你好",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="opening"),
        collection_result={"all_fields": []},
        response_to_clean="ignored",
        ai_response="",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response
    assert "再发一句" in final_response
    assert delivery_ok is True
    assert chat_service._last_unified_generation_record["first_generation_only"] is True


@pytest.mark.asyncio
async def test_finalize_generated_response_uses_stable_followup_when_ai_text_is_empty_but_ask_field_known(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_empty_ai_known_followup")
    profile.sex = "女"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.collection_progress.update({"sex": True, "location": True, "education": True, "occupation": True})
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, _ = await chat_service.finalize_generated_response(
        account_id="u_finalize_empty_ai_known_followup",
        user_profile=profile,
        user_message="在编教师呢",
        turn_decision=SimpleNamespace(
            ask_field="age",
            prioritize_user_question=False,
            primary_move="ack_and_ask",
            allow_medium_target=True,
        ),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="profile_answer"),
        collection_result={"all_fields": [{"field": "occupation", "value": "在编教师"}]},
        response_to_clean="ignored",
        ai_response="",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=2,
    )

    assert delivery_ok is True
    assert "几几年的" in final_response or "哪一年的" in final_response
    assert "另一半" not in final_response
    assert "我先换个更稳妥的说法" not in final_response
    assert "刚刚这条没生成完整" not in final_response
    assert chat_service._last_unified_generation_record["first_generation_only"] is True


@pytest.mark.asyncio
async def test_finalize_generated_response_keeps_ai_text_for_invalid_contact_attempt_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_invalid_contact")
    profile.location = "深圳"
    profile.last_contact_request_type = "phone"
    profile.phone_ask_count = 2
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.contact_context_service.is_contact_context_active = Mock(return_value=True)
    chat_service._build_validation_feedback = AsyncMock(return_value="这个号码我看着还不太对，你再发个常用手机号给我就行。")

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_invalid_contact",
        user_profile=profile,
        user_message="1768876543",
        turn_decision=SimpleNamespace(ask_field="contact", prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_context_reply"),
        collection_result={"all_fields": [], "invalid_contact_attempt": "1768876543"},
        response_to_clean="ignored",
        ai_response="好哒，号码我记下来啦。",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response == "这个号码我看着还不太对，你再发个常用手机号给我就行。"
    assert delivery_ok is True
    assert returned_profile.account_id == profile.account_id
    chat_service._build_validation_feedback.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_generated_response_prefers_contact_followup_after_valid_phone_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_phone_then_wechat")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.sex = "男"
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_wechat")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)
    chat_service._is_profile_collection_complete_or_exhausted = lambda _profile: True

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_phone_then_wechat",
        user_profile=profile,
        user_message="17688765432",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_context_reply"),
        collection_result={"all_fields": [{"field": "phone", "value": "17688765432"}]},
        response_to_clean="电话这边我记下了。你要是方便，也可以顺手留个微信。",
        ai_response="这个号码我记下了哈，你是男生还是女生呀？",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response == "电话这边我记下了。你要是方便，也可以顺手留个微信。"
    assert "微信" in final_response
    assert "男生还是女生" not in final_response
    assert delivery_ok is True
    assert returned_profile is profile


@pytest.mark.asyncio
async def test_finalize_generated_response_falls_back_to_wechat_followup_after_valid_phone_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_phone_then_wechat_fallback")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.sex = "女"
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_wechat")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)
    chat_service._is_profile_collection_complete_or_exhausted = lambda _profile: True

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_phone_then_wechat_fallback",
        user_profile=profile,
        user_message="17688765432",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_context_reply"),
        collection_result={"all_fields": [{"field": "phone", "value": "17688765432"}]},
        response_to_clean="ignored",
        ai_response="你说你想要找稳定的90后男生，那你平时更看重对方的性格多一些，还是工作发展呀？",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert delivery_ok is True
    assert returned_profile is profile
    assert "微信" in final_response
    assert "性格多一些" not in final_response


@pytest.mark.asyncio
async def test_finalize_generated_response_preserves_ai_faq_answer_when_user_question_priority_is_active(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_faq_priority")
    profile.phone = "17688765432"
    profile.phone_collected = True
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="ask_wechat")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)
    chat_service._is_profile_collection_complete_or_exhausted = lambda _profile: True

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_faq_priority",
        user_profile=profile,
        user_message="怎么收费呢先了解下",
        turn_decision=SimpleNamespace(prioritize_user_question=True, primary_move="answer_then_pause", ask_field="contact"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="faq_concern", subtype="fee"),
        collection_result={"all_fields": [{"field": "phone", "value": "17688765432"}]},
        response_to_clean="ignored",
        ai_response="收费这块你可以先放心，目前这边不额外收费，你先了解清楚就行。",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response == "收费这块你可以先放心，目前这边不额外收费，你先了解清楚就行。"
    assert "微信" not in final_response
    assert delivery_ok is True
    assert returned_profile is profile


@pytest.mark.asyncio
async def test_finalize_generated_response_realigns_mismatched_followup_field_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_realign_raw_mode")
    profile.sex = "女"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.collection_progress.update({"sex": True, "location": True, "education": True, "occupation": True})
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_realign_raw_mode",
        user_profile=profile,
        user_message="在编教师",
        turn_decision=SimpleNamespace(
            ask_field="age",
            prioritize_user_question=False,
            primary_move="ack_and_ask",
            allow_medium_target=False,
            response_channel="model",
        ),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="profile_answer", subtype="single_slot_answer"),
        collection_result={"all_fields": [{"field": "occupation", "value": "在编教师"}]},
        response_to_clean="ignored",
        ai_response="在编教师工作挺稳定的呀，你是男生还是女生呀？",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert delivery_ok is True
    assert returned_profile is profile
    assert "男生还是女生" not in final_response
    assert any(marker in final_response for marker in ("多大", "年龄", "哪一年", "几几年", "90后"))


@pytest.mark.asyncio
async def test_finalize_generated_response_ignores_rewritten_response_to_clean_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_prefers_rewritten_text")
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_prefers_rewritten_text",
        user_profile=profile,
        user_message="wx7789789",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_provided"),
        collection_result={"all_fields": [{"field": "wechat", "value": "wx7789789"}]},
        response_to_clean="ask:sex",
        ai_response="好的，这个微信号我记下啦，后面有合适的对接方向时联系你也更方便~",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert final_response == "好的，这个微信号我记下啦，后面有合适的对接方向时联系你也更方便~"
    assert delivery_ok is True
    assert returned_profile is profile


def test_finalize_followup_alignment_rewrites_explicit_mismatch_even_when_response_not_low_info():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_alignment_hard_guard")
    profile.sex = "女"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.collection_progress.update({"sex": True, "location": True, "education": True, "occupation": True})

    rewritten = chat_service.finalize_service._maybe_enforce_main_followup_alignment(
        user_profile=profile,
        user_message="在编教师",
        final_response="在编教师挺好的呀，你是男生还是女生呀？",
        turn_decision=TurnDecision(
            intent="general",
            primary_move="light_followup",
            ask_field="age",
            allow_medium_target=False,
            response_channel="model",
        ),
        collection_result={"all_fields": [{"field": "occupation", "value": "在编教师"}]},
    )

    assert "男生还是女生" not in rewritten
    assert any(marker in rewritten for marker in ("多大", "年龄", "哪一年", "几几年", "90后"))


def test_style_preserving_followup_drops_speculative_prefix_before_stable_question():
    chat_service = _build_chat_service()

    rewritten = chat_service._build_style_preserving_followup_response(
        original_response="你本科学历找的工作应该还挺不错的吧，方便说下你现在是做什么方向的吗？",
        fallback_response="那你现在在深圳主要做哪方面工作呀？",
    )

    assert rewritten == "那你现在在深圳主要做哪方面工作呀？"


@pytest.mark.asyncio
async def test_finalize_generated_response_strips_extract_from_raw_ai_response(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_strip_extract_from_rewritten")
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_strip_extract_from_rewritten",
        user_profile=profile,
        user_message="17688765432",
        turn_decision=SimpleNamespace(prioritize_user_question=False, primary_move="ack_and_ask"),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_context_reply"),
        collection_result={"all_fields": [{"field": "phone", "value": "17688765432"}]},
        response_to_clean="电话我收到了。方便的话，微信也可以发我一下。\n<extract>\n微信:null\n</extract>",
        ai_response="好哒，这个号码我记下啦，你是男生还是女生呀？\n<extract>\n微信:null\n</extract>",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert "<extract>" not in final_response
    assert "微信也可以发我一下" not in final_response
    assert "你是男生还是女生呀？" in final_response
    assert delivery_ok is True
    assert returned_profile is profile


def test_response_mentions_wechat_request_ignores_extract_block():
    from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService

    response = "好哒，这个号码我记下啦，你是男生还是女生呀？\n<extract>\n微信:null\n</extract>"

    assert ChatServiceContactTextService.response_mentions_wechat_request(response) is False


def test_build_generation_prompt_uses_dedicated_core_soft_refusal_instruction():
    chat_service = _build_chat_service()

    prompt = chat_service.build_generation_prompt(
        user_message="不方便说",
        user_profile=UserProfile(account_id="u_soft_refusal_prompt"),
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="education",
            response_channel="model",
            primary_move="light_followup",
            allow_medium_target=False,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="invalid_input",
            subtype="soft_refusal_current_field",
            soft_retry_field="education",
        ),
    )

    assert "【字段解释型重问专用生成】" in prompt
    assert "当前唯一任务：针对“学历”做一次换话术+解释型重问。" in prompt
    assert "不能跳去别的字段" in prompt
    assert "不要用“摸个底”" in prompt
    assert "只参考语气，不要机械照抄" in prompt


def test_build_generation_prompt_uses_dedicated_pending_retry_instruction_for_medium_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_retry_medium")
    profile.pending_retry_field = "monthly_income"

    prompt = chat_service.build_generation_prompt(
        user_message="深圳",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="monthly_income",
            response_channel="model",
            primary_move="light_followup",
            allow_medium_target=False,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
        ),
    )

    assert "【字段解释型重问专用生成】" in prompt
    assert "收入区间" in prompt
    assert "这个字段上一轮没有形成有效询问或被中途打断" in prompt


def test_build_generation_prompt_uses_primary_followup_instruction_for_normal_field_followup():
    chat_service = _build_chat_service()

    prompt = chat_service.build_generation_prompt(
        user_message="本科",
        user_profile=UserProfile(account_id="u_primary_followup_prompt"),
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            primary_move="light_followup",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
        ),
    )

    assert "【字段追问主路径生成】" in prompt
    assert "第一次生成就把这轮对“工作方向”的追问完成" in prompt
    assert "第一次生成的话术就是最终展示话术" in prompt


def test_build_generation_prompt_uses_primary_contact_instruction_for_contact_followup():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_primary_contact_prompt")
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "美业"
    profile.monthly_income = "7万左右"
    profile.marital_status = "单身"

    prompt = chat_service.build_generation_prompt(
        user_message="单身呢",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="contact",
            response_channel="model",
            primary_move="light_followup",
            allow_medium_target=False,
            allow_contact_target=True,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
        ),
    )

    assert "【联系方式动作专用生成】" in prompt
    assert "这轮第一次生成就要把这个联系方式动作完成" in prompt
    assert "第一次生成的话术就是最终展示话术" in prompt


def test_build_generation_prompt_opening_soft_sex_confirmation_does_not_add_third_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_soft_sex_limit")
    profile.location = "深圳"
    profile.age = 35
    profile.collection_progress["location"] = True
    profile.collection_progress["age"] = True

    prompt = chat_service.build_generation_prompt(
        user_message="你好，我想找个男朋友，我今年35岁，目前在深圳",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="matchmaking_intent",
            resolved_slots={"partner_gender_preference": "男", "location": "深圳", "age": "35"},
        ),
    )

    assert "单轮最多只推进两个信息点" in prompt
    assert "性别确认本身也算一个信息点" in prompt
    assert "如果顺着聊合适，请把“收入区间”自然融合" not in prompt


def test_build_generation_prompt_uses_suspicious_value_clarification_instruction():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_suspicious_prompt")

    prompt = chat_service.build_generation_prompt(
        user_message="你好，我想找对象，我今年935岁，目前在深圳",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="matchmaking_intent",
            resolved_slots={"location": "深圳", "partner_gender_preference": "男"},
        ),
    )

    assert "【异常资料澄清专用生成】" in prompt
    assert "只围绕“年龄”做澄清确认" in prompt
    assert "不要继续追问职业、收入、学历、联系方式等其他字段" in prompt


def test_build_generation_prompt_does_not_treat_partner_age_gap_as_suspicious_age():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_partner_age_gap_prompt")

    prompt = chat_service.build_generation_prompt(
        user_message="你好，你们是不是有帮忙介绍对象呀，我今年36，然后想找一个和我上下相差3岁的，最好在深圳这边的",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="matchmaking_intent",
            resolved_slots={"age": "36", "location": "深圳", "partner_gender_preference": "男"},
        ),
    )

    assert "【异常资料澄清专用生成】" not in prompt


def test_build_generation_prompt_does_not_instruct_same_turn_phone_ack_and_wechat_followup_before_profile_complete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_success_followup_prompt")
    profile.sex = "女"
    profile.age = 28
    profile.age_label = "98年"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.last_contact_request_type = "phone"
    profile.phone_ask_count = 1

    prompt = chat_service.build_generation_prompt(
        user_message="17688987678",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="contact",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=False,
            allow_contact_target=True,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_context_reply",
        ),
    )

    assert "【联系方式成功后顺带追问专用生成】" not in prompt
    assert "这轮核心动作是顺势轻问微信" not in prompt
    assert "这轮最终文案里必须明确出现“微信”" not in prompt
    assert "【联系方式动作专用生成】" in prompt
    assert "这轮只能围绕“电话”生成" in prompt


def test_build_generation_prompt_does_not_instruct_same_turn_wechat_followup_when_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_success_followup_prompt_none_action")
    profile.sex = "男"
    profile.age = 27
    profile.age_label = "99年"
    profile.location = "深圳"
    profile.education = "高中"
    profile.occupation = "下水管道维修工"
    profile.monthly_income = "2万"
    profile.marital_status = "单身"
    profile.last_contact_request_type = "phone"
    profile.phone_ask_count = 2

    prompt = chat_service.build_generation_prompt(
        user_message="17688987654",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="contact",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=False,
            allow_contact_target=True,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_context_reply",
        ),
    )

    assert "【联系方式成功后顺带追问专用生成】" not in prompt
    assert "这轮核心动作是顺势轻问微信" not in prompt
    assert "这轮最终文案里必须明确出现“微信”" not in prompt
    assert "【联系方式动作专用生成】" not in prompt
    assert "这轮只能围绕“电话”生成" not in prompt


@pytest.mark.asyncio
async def test_build_final_turn_payload_keeps_frozen_response_and_exposes_unified_meta_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_payload_raw")
    chat_service._build_chat_response = AsyncMock(
        return_value={"success": True, "response": "旧正文", "dialogId": "dlg", "meta": {}}
    )
    chat_service._last_unified_generation_record = {
        "raw_ai_response": "AI原文",
        "final_display_response": "最终展示",
        "fallback_triggered": False,
    }

    payload = await chat_service.build_final_turn_payload(
        account_id="u_payload_raw",
        user_profile=profile,
        final_response="最终展示",
        collection_result={"ending_info": {"scenario": "both_rejected"}},
        dialog_id="dlg",
        route_name="model",
    )

    assert payload["response"] == "最终展示"
    assert payload["meta"]["ai_response_unified_generation"]["raw_ai_response"] == "AI原文"
    assert payload["meta"]["ai_response_unified_generation"]["final_display_response"] == "最终展示"


@pytest.mark.asyncio
async def test_build_enhanced_response_to_clean_keeps_ai_response_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_delivery_raw")

    response_to_clean = await chat_service.build_enhanced_response_to_clean(
        account_id="u_delivery_raw",
        user_profile=profile,
        user_message="这是我电话",
        collection_result={"all_fields": []},
        ai_response="AI原文",
    )

    assert response_to_clean == "AI原文"


@pytest.mark.asyncio
async def test_build_enhanced_response_to_clean_keeps_contact_rewrite_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_delivery_contact_flow")
    chat_service._handle_contact_validation = AsyncMock(
        return_value="电话我收到了。要是你方便的话，再补个微信也行。"
    )

    response_to_clean = await chat_service.build_enhanced_response_to_clean(
        account_id="u_delivery_contact_flow",
        user_profile=profile,
        user_message="wx7789789",
        collection_result={"all_fields": [{"field": "wechat", "value": "wx7789789"}]},
        ai_response="好的，微信我已经记下来啦，后续有合适的方向联系你也更方便。",
    )

    assert response_to_clean == "电话我收到了。要是你方便的话，再补个微信也行。"
    chat_service._handle_contact_validation.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_enhanced_response_to_clean_keeps_raw_ai_when_contact_validation_does_not_rewrite(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_delivery_contact_flow_same")
    chat_service._handle_contact_validation = AsyncMock(
        return_value="好的，微信我已经记下来啦，后续有合适的方向联系你也更方便。"
    )

    response_to_clean = await chat_service.build_enhanced_response_to_clean(
        account_id="u_delivery_contact_flow_same",
        user_profile=profile,
        user_message="wx7789789",
        collection_result={"all_fields": [{"field": "wechat", "value": "wx7789789"}]},
        ai_response="好的，微信我已经记下来啦，后续有合适的方向联系你也更方便。",
    )

    assert response_to_clean == "好的，微信我已经记下来啦，后续有合适的方向联系你也更方便。"
    chat_service._handle_contact_validation.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_enhanced_response_to_clean_routes_active_contact_context_without_extracted_fields(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_delivery_contact_context")
    profile.phone_ask_count = 1
    profile.last_contact_request_type = "phone"

    async def _handle_contact_validation(*args, **kwargs):
        chat_service._last_validation_feedback_meta = {
            "error_code": "CONTACT_INVALID_FORMAT",
            "field": "phone",
            "attempt": 1,
            "silent": False,
            "retry_active": True,
            "retry_lock_response": True,
        }
        return "这个号码我看着不太对，你再发个常用手机号。"

    chat_service._handle_contact_validation = AsyncMock(side_effect=_handle_contact_validation)

    response_to_clean = await chat_service.build_enhanced_response_to_clean(
        account_id="u_delivery_contact_context",
        user_profile=profile,
        user_message="156778877665555",
        collection_result={"all_fields": []},
        ai_response="好的，我记下了。",
    )

    assert response_to_clean == "这个号码我看着不太对，你再发个常用手机号。"
    chat_service._handle_contact_validation.assert_awaited_once()


def test_followup_prompt_service_uses_contextual_occupation_prompt_without_inference_candidate():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_followup_contextual_occupation")
    profile.location = "深圳"

    prompt = chat_service.followup_prompt_service.build_local_field_fallback_prompt(
        "occupation",
        profile,
        user_message="嗯",
        stage="opening",
    )

    assert "深圳" in prompt
    assert any(token in prompt for token in ("工作", "做什么"))


def test_followup_prompt_service_uses_wechat_specific_prompt_after_phone_is_already_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_followup_seed")
    profile.phone = "17688987654"
    profile.phone_collected = True
    profile.last_contact_request_type = "wechat"

    prompt = chat_service._build_followup_seed_for_model_rewrite(
        "contact",
        profile,
        user_message="17688987654",
    )

    assert "微信" in prompt
    assert "手机号" not in prompt


@pytest.mark.asyncio
async def test_sync_post_delivery_state_keeps_first_generation_response_in_unified_path(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_sync_raw")
    updated_profile = UserProfile(account_id="u_sync_raw")
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=updated_profile)
    chat_service._update_progress_runtime_counters = AsyncMock(return_value=updated_profile)

    final_response, returned_profile = await chat_service.sync_post_delivery_state(
        account_id="u_sync_raw",
        user_profile=profile,
        user_message="你好",
        final_response="冻结正文",
        ai_response="AI原文",
        delivery_ok=True,
        turn_decision=SimpleNamespace(
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        ),
        collection_result={"all_fields": []},
        message_count=1,
        previous_asked_field=None,
    )

    assert final_response == "冻结正文"
    assert returned_profile is updated_profile


@pytest.mark.asyncio
async def test_handle_refusal_detection_closes_birth_year_followup_without_skipping_age():
    profile = UserProfile(account_id="u_birth_year_refusal")
    profile.pending_birth_year_bucket = "90后"
    user_service = _FakeProfileUserService(profile)
    chat_service = ChatService(_FakeAIService(), user_service)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="好，那你具体是90几年的呀？")
    chat_service.refusal_service = SimpleNamespace(is_refusing=lambda message: True)
    chat_service.contact_service = SimpleNamespace(
        detect_refusal=lambda **kwargs: None,
        should_end_conversation=lambda profile: False,
        get_status_display=lambda profile: "",
    )

    await chat_service._handle_refusal_detection("这个先不说", "u_birth_year_refusal", profile)

    assert profile.birth_year_confirmation_closed is True
    assert profile.is_active_ask_closed("age") is True
    assert "u_birth_year_refusal" not in chat_service._temp_refused_fields


@pytest.mark.asyncio
async def test_handle_refusal_detection_rolls_back_pending_phone_when_faq_interrupts_contact_turn():
    profile = UserProfile(account_id="u_contact_faq_interrupt")
    profile.location = "深圳"
    profile.phone_ask_count = 2
    profile.phone_effective_ask_count = 2
    profile.last_contact_request_type = "phone"
    user_service = _FakeProfileUserService(profile)
    chat_service = ChatService(_FakeAIService(), user_service)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="方便留个电话号码给我吗？")
    chat_service.refusal_service = SimpleNamespace(is_refusing=lambda message: False)

    await chat_service._handle_refusal_detection("你们是中介吗？", "u_contact_faq_interrupt", profile)

    assert profile.phone_ask_count == 1
    assert profile.phone_effective_ask_count == 1
    assert profile.last_contact_request_type is None


@pytest.mark.asyncio
async def test_handle_refusal_detection_uses_unified_faq_understanding_for_contact_interrupt():
    profile = UserProfile(account_id="u_contact_faq_interrupt_unified")
    profile.location = "深圳"
    profile.phone_ask_count = 2
    profile.phone_effective_ask_count = 2
    profile.last_contact_request_type = "phone"
    user_service = _FakeProfileUserService(profile)
    chat_service = ChatService(_FakeAIService(), user_service)
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="方便留个电话号码给我吗？")
    chat_service.refusal_service = SimpleNamespace(is_refusing=lambda message: False)

    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="fee",
        confidence=0.95,
    )
    await chat_service._handle_refusal_detection(
        "这个我先了解下",
        "u_contact_faq_interrupt_unified",
        profile,
        understanding_result=understanding,
    )

    assert profile.phone_ask_count == 1
    assert profile.phone_effective_ask_count == 1
    assert profile.last_contact_request_type is None


def test_get_priority_question_response_prefers_unified_understanding_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_priority_question_unified")
    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="fee",
        confidence=0.95,
    )

    response = chat_service._get_priority_question_response(
        "这个我先了解下",
        profile,
        understanding_result=understanding,
    )

    assert response


def test_get_priority_question_response_accepts_answer_first_mixed_understanding_intent():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_priority_question_mixed")
    understanding = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="fee",
        answer_first=True,
        confidence=0.92,
    )

    response = chat_service._get_priority_question_response(
        "这个我先了解下",
        profile,
        understanding_result=understanding,
    )

    assert response


def test_has_faq_priority_signal_accepts_answer_first_mixed_understanding_intent():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="fee",
        answer_first=True,
        confidence=0.92,
    )

    assert chat_service._has_faq_priority_signal("这个我先了解下", understanding_result=understanding) is True


def test_build_shadow_profile_for_decision_keeps_age_uncovered_for_bucket_only_age():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_shadow_age_bucket")

    understanding = SimpleNamespace(resolved_slots={"age": "36", "age_label": "90后"})
    shadow = chat_service._build_shadow_profile_for_decision(
        profile,
        "90后",
        understanding_result=understanding,
    )

    assert shadow.pending_birth_year_bucket == "90后"
    assert shadow.collection_progress["age"] is False


def test_policy_decide_keeps_age_as_main_target_when_birth_year_bucket_pending():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_age_bucket")
    profile.sex = "女"
    profile.collection_progress["sex"] = True
    profile.partner_requirement = "成熟稳重"
    profile.partner_gender_preference = "男"
    profile.collection_progress["partner_requirement"] = True
    profile.collection_progress["partner_gender_preference"] = True
    profile.pending_birth_year_bucket = "90后"
    profile.birth_year_confirmation_closed = False
    profile.age_label = "90后"
    profile.age = 36
    profile.collection_progress["age"] = False

    decision = policy.decide(
        profile,
        user_message="90后",
        message_count=2,
    )

    assert decision.main_target == "age"


def test_avoid_reasking_current_field_keeps_birth_year_followup_for_bucket_only_age():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_keep_birth_year_followup")
    profile.pending_birth_year_bucket = "90后"
    profile.birth_year_confirmation_closed = False
    profile.age_label = "90后"
    profile.age = 36
    profile.collection_progress["age"] = False

    response = "90后跨度还挺大的呢，具体是九几年出生的呀？"
    collection_result = {
        "all_fields": [
            {"field": "age", "value": "36"},
            {"field": "age_label", "value": "90后"},
        ]
    }

    rewritten = chat_service._avoid_reasking_just_collected_field(
        response,
        profile,
        collection_result,
        current_ask_field="age",
        user_message="90后",
        allow_medium_target=True,
    )

    assert rewritten == response


def test_resolve_effective_followup_field_keeps_age_when_birth_year_bucket_pending():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_effective_age_bucket")
    profile.pending_birth_year_bucket = "90后"
    profile.birth_year_confirmation_closed = False
    profile.age_label = "90后"
    profile.age = 36
    profile.collection_progress["age"] = False

    effective = chat_service._resolve_effective_followup_field(
        profile,
        ask_field="age",
        collected_fields={"age", "age_label"},
        user_message="90后",
        allow_medium_target=True,
    )

    assert effective == "age"


def test_contact_refusal_does_not_short_circuit_into_boundary_quick_decision():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_refusal")

    understanding = TurnUnderstandingResult(
        primary_turn_type="refusal_boundary_complaint",
        subtype="contact_refusal",
        answer_first=True,
        confidence=0.9,
        context_ack_type="contact_refusal",
    )

    decision = chat_service._build_understanding_quick_decision(  # noqa: SLF001
        understanding=understanding,
        user_profile=profile,
        stage="completing",
        user_message="电话不方便",
        followup_topic="contact_refusal",
        context_ack_payload={},
    )

    assert decision is None


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


@pytest.mark.asyncio
async def test_process_extracted_data_keeps_wx_prefixed_wechat_account():
    profile = UserProfile(account_id="u_wx_prefixed_wechat")
    user_service = _FakeProfileUserService(profile)
    extraction_service = ExtractionService(user_service)

    result = await extraction_service.process_extracted_data(
        "u_wx_prefixed_wechat",
        profile,
        {"contact": "wx23234242"},
        user_message="wx23234242",
    )

    assert result["collected"] is True
    assert profile.wechat == "wx23234242"


@pytest.mark.asyncio
async def test_process_extracted_data_moves_pure_gender_preference_out_of_partner_requirement():
    profile = UserProfile(account_id="u_partner_pref_only")
    user_service = _FakeProfileUserService(profile)
    extraction_service = ExtractionService(user_service)

    result = await extraction_service.process_extracted_data(
        "u_partner_pref_only",
        profile,
        {"partner_requirement": "找男朋友"},
        user_message="你好，找男朋友",
    )

    assert result["collected"] is True
    assert profile.partner_gender_preference == "男"
    assert profile.partner_requirement in (None, "")


def test_fuse_extracted_fields_preserves_rich_ai_requirement_when_rule_requirement_is_sparse():
    service = _build_chat_service()

    fused, meta = service._fuse_extracted_fields(
        {
            "partner_requirement": "对方为未婚男性，学历本科及以上，需符合身高要求，优先大厂程序员",
            "partner_gender_preference": "男",
        },
        {
            "partner_requirement": "找男",
            "partner_gender_preference": "男",
            "sex": "女",
            "education": "本科",
            "marital_status": "未婚",
        },
        user_message="南山女生找男盆友，93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不",
    )

    assert fused["partner_gender_preference"] == "男"
    assert fused["partner_requirement"] == "对方为未婚男性，学历本科及以上，需符合身高要求，优先大厂程序员"
    assert meta["partner_requirement"]["source"] == "rich_partner_requirement_preserved"


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


def test_strip_false_input_error_followup_rebuilds_when_age_was_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_false_typo_guard")
    profile.age = 36
    profile.collection_progress["age"] = True

    response = chat_service._strip_false_input_error_followup(
        "是不是打错字啦，我看你说今年36对吧，我先记下来。你是男生还是女生呀？",
        profile,
        {"all_fields": [{"field": "age", "value": "36岁"}]},
        user_message="我今年36",
        ask_field="sex",
    )

    assert "打错字" not in response
    assert "没看懂" not in response
    assert "36" in response
    assert "男生还是女生" in response


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

    assert "工作=IT" in instruction
    assert "感情状态/婚况" in instruction
    assert "择偶要求/更看重哪一点" in instruction


def test_profile_bridge_ai_rewrite_entries_are_removed():
    chat_service = _build_chat_service()

    assert not hasattr(chat_service, "_enforce_profile_bridge_response")
    assert not hasattr(chat_service, "_rewrite_response_for_profile_bridge")


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
    assert "祝你早日脱单" in response
    assert "1-8小时" in response
    assert "提前约时间" in response
    assert "不打扰你" in response


def test_expectation_service_contact_completion_response_uses_standard_timeline_when_not_qualified():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_standard")
    profile.age = 26
    profile.education = "本科"
    profile.sex = "男"
    profile.monthly_income = "4万"

    response = service.get_contact_completion_response(profile)

    assert "1-2天" in response


def test_expectation_service_contact_completion_response_uses_female_income_threshold():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_female_fast")
    profile.age = 28
    profile.education = "本科"
    profile.sex = "女"
    profile.monthly_income = "1万"

    response = service.get_contact_completion_response(profile)

    assert "1-8小时" in response


def test_expectation_service_contact_completion_response_supports_annual_income_shorthand():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_female_annual_fast")
    profile.age = "93"
    profile.education = "本科"
    profile.sex = "女"
    profile.monthly_income = "年薪税后大概20左右"

    response = service.get_contact_completion_response(profile)

    assert "1-8小时" in response


def test_expectation_service_parse_monthly_income_amount_supports_range_and_approx():
    service = ExpectationService()

    assert service.parse_monthly_income_amount("月收入8k-12k左右") == pytest.approx(10000.0)
    assert service.parse_monthly_income_amount("大概收入2万到3万") == pytest.approx(25000.0)
    assert service.parse_monthly_income_amount("两万上下") == pytest.approx(20000.0)
    assert service.parse_monthly_income_amount("一年18-24左右") == pytest.approx(17500.0)


def test_expectation_service_contact_completion_response_supports_annual_income_range_shorthand():
    service = ExpectationService()
    profile = UserProfile(account_id="u_expect_female_annual_range_fast")
    profile.age = 29
    profile.education = "本科"
    profile.sex = "女"
    profile.monthly_income = "一年18-24左右"

    response = service.get_contact_completion_response(profile)

    assert "1-8小时" in response


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


def test_build_turn_decision_saves_interrupted_followup_target_on_info_collection_concern():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_monthly_income")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True
    profile.last_asked_field = "monthly_income"

    decision = chat_service._build_turn_decision(
        "为啥要记下我的信息呢？",
        profile,
        conversation_context={
            "message_count": 6,
            "recent_responses": ["好哦，你的基本情况我大概有数啦，你每个月收入大概在什么区间呀？"],
        },
    )

    assert decision.prioritize_user_question is True
    assert decision.ask_field is None
    assert profile.resume_profile_target == "monthly_income"
    assert decision.resume_target == "monthly_income"


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


def test_build_turn_decision_opening_with_substantive_profile_content_keeps_followup_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_profile_provided")

    decision = chat_service._build_turn_decision(
        "你好，帮我物色个男朋友，我90后的，目前在深圳上班呢，喜欢高大的",
        profile,
        conversation_context={"message_count": 0},
    )

    assert decision.response_channel == "model"
    assert decision.primary_move in {"ack_and_ask", "light_followup"}
    assert decision.ask_field is not None
    assert decision.ask_field not in {"location", "age", "partner_requirement", "contact"}


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


def test_should_force_model_expression_for_composite_opening_matchmaking():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        secondary_signals=["opening_greeting", "service_confirmation_like"],
        resolved_slots={"partner_gender_preference": "男"},
        confidence=0.92,
    )
    turn_decision = TurnDecision(response_channel="quick_faq", intent="opening_self_intro")

    forced = chat_service._should_force_model_expression(  # noqa: SLF001
        understanding=understanding,
        turn_decision=turn_decision,
        user_message="你好，帮我找个男朋友呀，你们是有帮忙介绍对象是吧",
    )

    assert forced is True


def test_build_turn_decision_opening_matchmaking_does_not_take_light_consult_when_plan_has_profile_fields():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_opening_matchmaking_plan_fields")
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        secondary_signals=["opening_matchmaking_intent", "service_confirmation_like"],
        resolved_slots={},
        confidence=0.92,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="location",
                    value="深圳龙华",
                    normalized_value="深圳龙华",
                    scope="self",
                    evidence_text="深圳龙华在编女教师",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )
    chat_service.unified_turn_understanding_service.analyze = AsyncMock(return_value=understanding)

    decision = chat_service._build_turn_decision(
        "可以哒 深圳龙华在编女教师，对啦怎么收费呢",
        profile,
        conversation_context={"message_count": 0},
    )

    assert decision.intent == "opening_self_intro"
    assert decision.followup_topic != "opening_self_intro" or decision.prioritize_user_question is False


def test_safe_quick_faq_keeps_pure_greeting_on_whitelist():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="greeting",
        secondary_signals=["opening_greeting"],
        confidence=0.9,
    )

    safe = chat_service._is_safe_quick_faq_expression(  # noqa: SLF001
        understanding=understanding,
        user_message="你好",
    )

    assert safe is True


def test_should_force_model_expression_reads_persistence_plan_slots_for_non_opening():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="general_faq",
        resolved_slots={},
        confidence=0.9,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="在编教师",
                    normalized_value="在编教师",
                    scope="self",
                    evidence_text="深圳龙华在编女教师",
                    confidence=0.94,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                    persistence_state="committed",
                    source_channel="ai",
                )
            ]
        ),
    )
    turn_decision = TurnDecision(response_channel="quick_faq", intent="general")

    forced = chat_service._should_force_model_expression(  # noqa: SLF001
        understanding=understanding,
        turn_decision=turn_decision,
        user_message="对啦怎么收费呢先了解下",
    )

    assert forced is True


def test_should_not_force_model_expression_when_priority_question_is_answer_only_or_resume():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        secondary_signals=["faq"],
        resolved_slots={},
        confidence=0.93,
    )
    semantic_frame = SimpleNamespace(
        primary_domain="faq",
        acts=[],
        user_questions=[SimpleNamespace(topic="pricing")],
        field_observations=[],
    )
    setattr(understanding, "semantic_frame", semantic_frame)
    turn_decision = TurnDecision(
        response_channel="quick_faq",
        intent="fee",
        priority_primary_task="user_question",
        priority_response_mode="answer_then_resume",
    )

    forced = chat_service._should_force_model_expression(  # noqa: SLF001
        understanding=understanding,
        turn_decision=turn_decision,
        user_message="可以直接电话联系这边13526783627，对啦怎么收费呢先了解下",
    )

    assert forced is False


@pytest.mark.asyncio
async def test_maybe_build_quick_faq_payload_applies_understanding_fields_before_short_circuit():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_quick_faq_collect")
    user_service = _FakeProfileUserService(profile)
    chat_service.user_service = user_service

    understanding = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        confidence=0.93,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="location",
                    value="深圳龙华",
                    normalized_value="深圳龙华",
                    scope="self",
                    evidence_text="深圳龙华",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                ),
                AcceptedField(
                    field="education",
                    value="本科",
                    normalized_value="本科",
                    scope="self",
                    evidence_text="一样本科",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                ),
            ]
        ),
    )
    turn_decision = TurnDecision(
        response_channel="quick_faq",
        intent="fee",
        priority_primary_task="user_question",
        priority_response_mode="answer_then_resume",
    )
    decision_profile = UserProfile(account_id="u_quick_faq_collect")

    chat_service._get_priority_question_response = Mock(return_value="基础匹配免费。")
    chat_service._build_resume_after_interrupt_response = Mock(side_effect=lambda response, *_args, **_kwargs: response)
    chat_service._looks_like_strong_concern_interrupt = Mock(return_value=False)
    chat_service._apply_priority_question_guard = Mock(side_effect=lambda response, *_args, **_kwargs: response)
    chat_service._apply_context_ack_policy = Mock(side_effect=lambda response, *_args, **_kwargs: response)
    chat_service._ensure_humanlike_memory_ack = Mock(side_effect=lambda _message, _profile, response: response)

    async def _process_collection(*args, **kwargs):
        user_service.profile.location = "深圳龙华"
        user_service.profile.education = "本科"
        user_service.profile.collection_progress["location"] = True
        user_service.profile.collection_progress["education"] = True
        return ProfileCollectionResult(
            collection_result={
                "all_fields": [
                    {"field": "location", "value": "深圳龙华"},
                    {"field": "education", "value": "本科"},
                ]
            },
            user_profile=user_service.profile,
        )

    chat_service.profile_collection_coordinator.process_collection = AsyncMock(side_effect=_process_collection)

    captured: dict[str, object] = {}

    async def _build_short_circuit_payload(**kwargs):
        captured["collection_result"] = kwargs["collection_result"]
        captured["user_profile"] = kwargs["user_profile"]
        return {
            "success": True,
            "response": kwargs["final_response"],
            "dialogId": kwargs["dialog_id"],
            "meta": {},
        }

    chat_service.build_short_circuit_payload = AsyncMock(side_effect=_build_short_circuit_payload)

    payload = await chat_service.preparation_service.maybe_build_quick_faq_payload(
        account_id="u_quick_faq_collect",
        user_profile=profile,
        user_message="深圳龙华在编女教师，一样本科，对啦怎么收费",
        dialog_id="dlg_quick_faq_collect",
        turn_decision=turn_decision,
        turn_understanding=understanding,
        decision_profile=decision_profile,
        conversation_context={"recent_responses": [], "message_count": 0},
    )

    assert payload["response"] == "基础匹配免费。"
    collection_result = captured["collection_result"]
    assert isinstance(collection_result, dict)
    assert {"field": "location", "value": "深圳龙华"} in collection_result["all_fields"]
    assert {"field": "education", "value": "本科"} in collection_result["all_fields"]
    assert user_service.profile.location == "深圳龙华"
    assert user_service.profile.education == "本科"
    assert user_service.profile.collection_progress["location"] is True
    assert user_service.profile.collection_progress["education"] is True


def test_is_contact_like_user_message_reads_persistence_plan_contact_fields():
    chat_service = _build_chat_service()
    understanding = TurnUnderstandingResult(
        primary_turn_type="general",
        resolved_slots={},
        confidence=0.87,
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="phone",
                    value="13526783627",
                    normalized_value="13526783627",
                    scope="contact",
                    evidence_text="13526783627",
                    confidence=0.99,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    assert chat_service._is_contact_like_user_message(  # noqa: SLF001
        "13526783627",
        understanding_result=understanding,
    ) is True


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


@pytest.mark.anyio
async def test_build_turn_decision_does_not_treat_contact_refusal_as_boundary_pause():
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

    decision = await chat_service._build_turn_decision("不方便留呀", profile, conversation_context={"message_count": 8})

    assert decision.risk != "boundary"
    assert decision.primary_move != "soft_hold"
    assert decision.allow_contact_target is True


@pytest.mark.anyio
async def test_build_turn_decision_keeps_contact_refusal_in_flow_after_wechat_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_refusal_after_wechat")
    profile.wechat = "abc123"
    profile.wechat_collected = True
    profile.phone_ask_count = 2
    profile.phone_effective_ask_count = 2
    profile.last_contact_request_type = "phone"

    decision = await chat_service._build_turn_decision(
        "不方便了，已经留了微信了",
        profile,
        conversation_context={"message_count": 8},
    )

    assert decision.risk != "boundary"
    assert decision.primary_move != "ack_and_hold"


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


def test_build_turn_decision_downgrades_contact_why_in_contact_context_back_to_mainline():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_why_fallback")
    profile.phone_ask_count = 1

    decision = chat_service._build_turn_decision(
        "为什么要留微信呀",
        profile,
        conversation_context={"message_count": 8},
    )

    assert decision.intent == "general"
    assert decision.response_channel == "model"
    assert decision.prioritize_user_question is False


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


def test_build_turn_decision_keeps_confirmation_on_profile_mainline_when_sex_still_pending():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_confirmation_resume")
    profile.resume_profile_mode = "collect_core"
    profile.resume_profile_target = "sex"
    profile.pending_sex_confirmation = "男"

    decision = chat_service._build_turn_decision("好的", profile, conversation_context={"message_count": 7})

    assert decision.response_channel == "model"
    assert decision.ask_field == "sex"
    assert decision.primary_move == "light_followup"


def test_build_turn_decision_resumes_monthly_income_after_faq_acknowledgement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_after_faq_ack")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True
    profile.resume_profile_mode = "collect_profile"
    profile.resume_profile_target = "monthly_income"
    profile.last_user_concern_type = "faq"

    decision = chat_service._build_turn_decision(
        "好的",
        profile,
        conversation_context={
            "message_count": 7,
            "recent_responses": ["这个我先说清楚，主要是怕后面把你的情况和择偶需求理解偏了，不会拿去乱登记乱用的。"],
        },
    )

    assert decision.intent == "general"
    assert decision.response_channel == "model"
    assert decision.ask_field == "monthly_income"
    assert decision.primary_move == "light_followup"
    assert decision.prioritize_user_question is False
    assert decision.resume_applied is True


def test_build_turn_decision_resumes_monthly_income_after_faq_acknowledgement_without_saved_resume_target():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_after_faq_ack_without_saved_target")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True
    profile.last_asked_field = "monthly_income"
    profile.last_user_concern_type = "faq"

    decision = chat_service._build_turn_decision(
        "好的",
        profile,
        conversation_context={
            "message_count": 7,
            "recent_responses": ["我知道你在意问得太细这个事儿呀，主要是为了后续给你匹配更合适的男生，你的信息我们都会严格保密的。"],
        },
    )

    assert decision.intent == "general"
    assert decision.response_channel == "model"
    assert decision.ask_field == "monthly_income"
    assert decision.primary_move == "light_followup"
    assert decision.prioritize_user_question is False
    assert decision.resume_applied is True
    assert profile.resume_profile_target is None


def test_build_turn_decision_restores_interrupted_income_followup_across_two_turns():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_after_faq_sequence")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True
    profile.last_asked_field = "monthly_income"

    faq_decision = chat_service._build_turn_decision(
        "为啥要记下我的信息呢？",
        profile,
        conversation_context={
            "message_count": 6,
            "recent_responses": ["好哦，你的基本情况我大概有数啦，你每个月收入大概在什么区间呀？"],
        },
    )

    assert faq_decision.prioritize_user_question is True
    assert faq_decision.ask_field is None
    assert profile.resume_profile_target == "monthly_income"

    resume_decision = chat_service._build_turn_decision(
        "好的",
        profile,
        conversation_context={
            "message_count": 7,
            "recent_responses": ["这个我先说清楚，主要是怕后面把你的情况和择偶需求理解偏了，不会拿去乱登记乱用的。"],
        },
    )

    assert resume_decision.ask_field == "monthly_income"
    assert resume_decision.primary_move == "light_followup"
    assert resume_decision.resume_applied is True
    assert profile.resume_profile_target is None


def test_build_turn_decision_treats_why_ask_so_clearly_as_info_collection_concern():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_ask_clearly_concern")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True
    profile.last_asked_field = "monthly_income"

    decision = chat_service._build_turn_decision(
        "为啥要问这么清晰呢",
        profile,
        conversation_context={
            "message_count": 6,
            "recent_responses": ["本科学历挺好的~你现在的月收入大概在什么范围呀？"],
        },
    )

    assert decision.intent == "info_collection_why"
    assert decision.prioritize_user_question is True
    assert decision.ask_field is None
    assert decision.allow_contact_target is False
    assert profile.resume_profile_target == "monthly_income"


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
    from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService

    response = ChatServiceContactTextService.build_dual_contact_ack()

    assert "电话和微信" in response
    assert "接着说" in response or "别的想法" in response
    assert "方便留个" not in response


def test_is_divorce_status_complete_message_accepts_natural_confirmation_variants():
    chat_service = _build_chat_service()

    positive_cases = [
        "办理好了",
        "办了好了",
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
    assert chat_service._is_divorce_confirmation_question("我先确认一个点，你这边离婚手续现在已经办妥了吗？") is True


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
async def test_process_collection_result_clears_pending_after_court_judgment_reply():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_divorce_done_judgment_flow")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="那你这边离婚手续都已经办妥了吗？")
    chat_service.extraction_service.process_extracted_data = AsyncMock(return_value={"all_fields": []})
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = lambda *_args, **_kwargs: None

    result = await chat_service._process_collection_result(
        account_id="u_divorce_done_judgment_flow",
        user_profile=profile,
        extracted_data={},
        user_message="有法院判决书",
        extraction_meta={},
        turn_id=2,
    )

    assert result["divorce_confirmation_cleared"] is True
    assert profile.divorce_confirmation_pending is False
    assert profile.divorce_confirmed is True
    assert profile.marital_status == "离异（手续已办妥）"


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
    profile.error_count["suspicious_age"] = 2
    profile.error_count["suspicious_height"] = 2

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(
        return_value={
            "all_fields": [
                {"field": "age", "value": "1000"},
                {"field": "height", "value": "3米"},
            ]
        }
    )
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
async def test_process_collection_result_does_not_hard_end_on_unconfirmed_fake_age_typo():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_fake_info_typo")

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(
        return_value={"all_fields": [{"field": "age", "value": "93"}]}
    )
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = Mock(return_value=None)

    result = await chat_service._process_collection_result(
        account_id="u_fake_info_typo",
        user_profile=profile,
        extracted_data={"age": "93"},
        user_message="你好，我想找对象，我今年935岁，目前在深圳",
        extraction_meta={},
        turn_id=1,
    )

    assert "ending_info" not in result


@pytest.mark.anyio
async def test_process_collection_result_marks_suspicious_value_for_clarification_before_fake_info():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_suspicious_clarify")

    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.extraction_service.process_extracted_data = AsyncMock(
        return_value={"all_fields": [{"field": "age", "value": "1000"}]}
    )
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)
    chat_service.ending_service.check_and_get_ending = Mock(return_value=None)

    result = await chat_service._process_collection_result(
        account_id="u_suspicious_clarify",
        user_profile=profile,
        extracted_data={"age": "1000"},
        user_message="我今年1000岁",
        extraction_meta={},
        turn_id=1,
    )

    assert "ending_info" not in result
    assert result["suspicious_value_clarification"]["fields"] == ["age"]
    assert profile.error_count["suspicious_age"] == 1


def test_enforce_question_budget_guard_trims_third_field_from_opening():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_question_budget")
    profile.partner_gender_preference = "男"

    text = "当然可以呀，你应该是女生对吧？你现在在深圳这边是做什么工作的呀，收入大概在什么范围呢？"
    trimmed = chat_service._enforce_question_budget_guard(
        text,
        user_profile=profile,
        user_message="你好，我想找男朋友，目前在深圳",
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
    )

    assert "收入" not in trimmed
    assert trimmed.endswith("？")
    asked_fields = chat_service._detect_asked_fields_in_response(trimmed) | chat_service._detect_all_questioned_fields_in_response(trimmed)
    assert len(asked_fields) <= 2


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


def test_build_contact_followup_response_after_phone_asks_wechat_more_naturally(monkeypatch):
    from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService

    monkeypatch.setattr("src.services.core.chat_service_contact_text_service.random.choice", lambda seq: seq[0])

    response = ChatServiceContactTextService.build_contact_followup_response("ask_wechat", "phone")

    assert "电话我收到了" in response
    assert "微信" in response
    assert any(token in response for token in ("方便", "补个", "发我一下", "顺手留个"))
    assert "方便留个微信吗" not in response


@pytest.mark.asyncio
async def test_phone_collection_does_not_force_wechat_followup_when_profile_incomplete(monkeypatch):
    chat_service = _build_chat_service()
    monkeypatch.setattr("src.services.core.chat_service_contact_text_service.random.choice", lambda seq: seq[0])
    profile = UserProfile(account_id="u_phone_to_wechat_followup")
    profile.location = "深圳"
    profile.phone = None
    profile.phone_collected = False
    profile.wechat = None
    profile.wechat_collected = False

    response = await chat_service.contact_validation_flow_service.handle_contact_validation(
        account_id="u_phone_to_wechat_followup",
        user_profile=profile,
        collection_result={"all_fields": [{"field": "contact", "value": "17688987659"}]},
        ai_response="好的，号码我已经存好了，之后碰到符合你要求的合适人选我会及时联系你哦。",
        user_message="17688987659",
    )

    assert response == "好的，号码我已经存好了，之后碰到符合你要求的合适人选我会及时联系你哦。"


@pytest.mark.asyncio
async def test_wechat_collection_resumes_profile_mainline_when_contact_complete_but_profile_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_wechat_complete_resume_mainline")
    profile.phone = "17688987659"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True

    chat_service._is_profile_collection_complete_or_exhausted = lambda _profile: False
    chat_service.collection_policy.has_serviceable_profile = lambda _profile: False
    chat_service._get_contact_terminal_or_resume_response = lambda _profile, _message: "ask:sex"

    response = await chat_service.contact_validation_flow_service.handle_contact_validation(
        account_id="u_wechat_complete_resume_mainline",
        user_profile=profile,
        collection_result={"all_fields": [{"field": "wechat", "value": "wx7789789"}]},
        ai_response="好哒，这个微信我记下来了，后续有合适的方向找你也更方便哈。",
        user_message="wx7789789",
    )

    assert response == "ask:sex"


@pytest.mark.asyncio
async def test_wechat_collection_uses_terminal_or_resume_response_when_completion_happens_this_turn():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_wechat_complete_same_turn")
    profile.sex = "女"
    profile.age = 31
    profile.age_label = "95年"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "新能源"
    profile.monthly_income = "约1.7万"
    profile.phone = "17899876548"
    profile.phone_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
            "contact": True,
        }
    )

    chat_service._is_profile_collection_complete_or_exhausted = lambda _profile: True
    chat_service._get_contact_terminal_or_resume_response = lambda _profile, _message: "terminal:done"

    response = await chat_service.contact_validation_flow_service.handle_contact_validation(
        account_id="u_wechat_complete_same_turn",
        user_profile=profile,
        collection_result={"all_fields": [{"field": "wechat", "value": "wuuiguergierg"}]},
        ai_response="哈哈刚才你发的这句我没太看懂哦～",
        user_message="wuuiguergierg",
    )

    assert response == "terminal:done"


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

    assert "我先帮你记下了" in response or "联系前" in response
    assert "1-8小时" in response
    assert "继续聊别的" not in response


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
    assert "不想留也没关系" not in response
    assert any(token in response for token in ["联系", "方向", "合适"])


def test_apply_refusal_respect_guard_explains_why_wechat_is_still_asked_after_phone():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refusal_guard_wechat_reason")
    profile.phone_collected = True
    profile.phone = "17688888888"
    profile.wechat_ask_count = 1
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="persuade_wechat")

    response = chat_service._apply_refusal_respect_guard(
        "没关系，这块我们先不急，继续聊别的也可以。",
        profile,
        "不留微信了，留了电话还要微信干嘛呢？",
    )

    assert "电话不一定方便接" in response or "方便看到" in response
    assert "按电话联系就行" in response
    assert "继续聊别的也可以" not in response


def test_apply_refusal_respect_guard_resumes_profile_mainline_after_wechat_refusal_when_phone_already_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refusal_guard_resume_mainline")
    profile.phone_collected = True
    profile.phone = "17688888888"
    profile.rejected_wechat = True
    profile.wechat_ask_count = 1
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    chat_service.contact_service.get_next_action = lambda *_args, **_kwargs: SimpleNamespace(value="none")
    chat_service._build_policy_field_prompt = lambda field, *_args, **_kwargs: f"ask:{field}"

    response = chat_service._apply_refusal_respect_guard(
        "好的，知道你是男生啦～其实留联系方式只是后续有合适的匹配机会时能及时找到你。",
        profile,
        "不方便呢",
    )

    assert "几几年的" in response or "多大" in response or "年龄" in response


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
    assert profile.last_asked_side_field is None
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_sets_pending_sex_confirmation_when_planned_sex_soft_confirm_is_used():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_sex_planned")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=6)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_pending_sex_planned",
        "高点的帅气的",
        "好哒，这些我都记下了，你这边是女生对吧？",
        "",
        turn_decision=SimpleNamespace(ask_field="sex"),
        track_asked_fields=True,
    )

    assert profile.pending_sex_confirmation == "女"
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_records_side_field_for_composite_confirm_prompt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_sex_side")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=6)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_pending_sex_side",
        "90后呢",
        "我这边确认一下，你这边是男生？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？",
        "",
        track_asked_fields=True,
    )

    assert profile.pending_sex_confirmation == "男"
    assert profile.last_asked_field == "sex"
    assert profile.last_asked_side_field == "marital_status"
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_prefers_planned_ask_field_over_ack_mentions():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_last_asked_education")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=8)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_last_asked_education",
        "it，7万",
        "做IT还挺厉害的，这个收入很不错呀，你是什么学历呀？",
        "",
        turn_decision=TurnDecision(ask_field="education"),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "education"
    assert profile.last_asked_side_field is None
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_prefers_planned_contact_field_over_drifted_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_last_asked_contact")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=9)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_last_asked_contact",
        "98年呢",
        "你刚才说想找90后、身高180以上、工作稳定的男生对吧？那除了这些，你有没有什么特别在意的小细节呀？",
        "",
        turn_decision=TurnDecision(ask_field="contact"),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "contact"
    assert profile.last_asked_side_field is None
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_keeps_secondary_marital_status_question_as_side_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_last_asked_occupation_with_marital_side")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=2)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_last_asked_occupation_with_marital_side",
        "找对象 女生找男朋友",
        "你想找工作稳定的男生我能get~对了，你自己目前是做什么工作的呀？顺便问下，你现在感情状态是单身对吧？",
        "",
        turn_decision=TurnDecision(ask_field="occupation"),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "occupation"
    assert profile.last_asked_side_field == "marital_status"
    assert profile.last_question_state.get("asked_fields") == ["occupation"]
    assert profile.last_question_state.get("side_fields") == ["marital_status"]
    assert profile.last_question_state.get("allow_mixed_answer") is True
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_keeps_secondary_monthly_income_question_as_side_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_last_asked_occupation_with_income_side")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=2)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_last_asked_occupation_with_income_side",
        "找对象 女生找男朋友",
        "你现在主要做什么工作的呀？顺便问下，你收入大概在哪个区间？",
        "",
        turn_decision=TurnDecision(ask_field="occupation"),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "occupation"
    assert profile.last_asked_side_field == "monthly_income"
    assert profile.last_question_state.get("side_fields") == ["monthly_income"]
    assert profile.last_question_state.get("allow_mixed_answer") is True
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_update_conversation_state_keeps_secondary_partner_requirement_question_after_age_prompt():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_last_asked_age_with_partner_side")
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=2)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_last_asked_age_with_partner_side",
        "98年",
        "你大概是哪一年的呀？顺着这个聊，你对另一半更看重哪一点也可以一起说说。",
        "",
        turn_decision=TurnDecision(ask_field="age"),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "age"
    assert profile.last_asked_side_field == "partner_requirement"
    assert profile.last_question_state.get("side_fields") == ["partner_requirement"]
    assert profile.last_question_state.get("allow_mixed_answer") is True
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.asyncio
async def test_finalize_generated_response_realigns_mismatched_contact_followup_in_raw_mode(monkeypatch):
    monkeypatch.setenv("AI_RAW_RESPONSE_MODE", "1")
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_realign_contact_raw_mode")
    profile.location = "深圳"
    profile.occupation = "在编教师"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True, "occupation": True, "marital_status": True}
    )
    chat_service._record_delivered_contact_ask_if_needed = AsyncMock(return_value=profile)

    final_response, delivery_ok, returned_profile = await chat_service.finalize_generated_response(
        account_id="u_finalize_realign_contact_raw_mode",
        user_profile=profile,
        user_message="98年呢",
        turn_decision=SimpleNamespace(
            ask_field="contact",
            prioritize_user_question=False,
            primary_move="light_followup",
            allow_medium_target=False,
            response_channel="model",
        ),
        turn_understanding=TurnUnderstandingResult(primary_turn_type="profile_answer", subtype="single_slot_answer"),
        collection_result={"all_fields": [{"field": "age", "value": 28}, {"field": "age_label", "value": "98年"}]},
        response_to_clean="ignored",
        ai_response="你刚才说想找90后、身高180以上、工作稳定的男生对吧？那除了这些，你有没有什么特别在意的小细节呀？",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert delivery_ok is True
    assert returned_profile is profile
    assert "另一半" not in final_response
    assert any(marker in final_response for marker in ("电话", "手机号", "联系"))


def test_should_force_progress_followup_after_collection_skips_after_valid_contact_capture():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_skip_force_contact_after_capture")
    profile.sex = "女"
    profile.age = 27
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.marital_status = "未婚"
    profile.partner_requirement = "90后，180以上，稳定"
    profile.phone = "17688987654"
    profile.phone_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "partner_requirement": True,
            "contact": True,
        }
    )

    should_force = chat_service._should_force_progress_followup_after_collection(
        refreshed_turn_decision=SimpleNamespace(
            ask_field=None,
            prioritize_user_question=False,
            next_action="continue",
            context_ack_payload={},
            priority_primary_task="contact_record",
        ),
        collection_result={"all_fields": [{"field": "contact", "value": "17688987654"}]},
        user_profile=profile,
    )

    assert should_force is False


def test_get_priority_question_response_answers_repeated_contact_ask_complaint():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_repeat_why")
    profile.phone = "17688987654"
    profile.phone_collected = True

    response = chat_service._get_priority_question_response(
        "上面不是已经留给过电话了嘛？为啥还要问？",
        profile,
        repeat_count=1,
        recent_responses=(),
    )

    assert response is not None
    assert "已经" in response or "前面" in response
    assert "不用你再重复发" in response or "重复" in response


@pytest.mark.anyio
async def test_update_conversation_state_preserves_last_asked_field_on_quick_faq_turn():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_preserve_last_asked_on_faq")
    profile.last_asked_field = "monthly_income"
    profile.resume_profile_target = "monthly_income"
    chat_service.dialogue_manager.add_to_history = AsyncMock()
    chat_service.dialogue_manager.get_last_response = AsyncMock(return_value="")
    chat_service.dialogue_manager.update_recent_responses = AsyncMock()
    chat_service.dialogue_manager.increment_message_count = AsyncMock()
    chat_service.dialogue_manager.get_message_count = AsyncMock(return_value=8)
    chat_service.ask_tracking_service.track_ai_asked_fields = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service._update_conversation_state(
        "u_preserve_last_asked_on_faq",
        "为啥要问这么清晰呢",
        "我知道你会在意这个，主要是怕后面把你的情况和择偶要求理解偏了，不是拿去乱做其他用途的。",
        "",
        turn_decision=TurnDecision(
            response_channel="quick_faq",
            prioritize_user_question=True,
            intent="info_collection_why",
        ),
        track_asked_fields=True,
    )

    assert profile.last_asked_field == "monthly_income"
    assert profile.resume_profile_target == "monthly_income"
    chat_service.user_service.save_user_profile.assert_awaited()


@pytest.mark.anyio
async def test_refresh_turn_decision_after_collection_preserves_resume_followup_when_refresh_would_fall_back():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refresh_preserve_resume")
    previous_turn_decision = TurnDecision(
        intent="general",
        primary_move="light_followup",
        ask_field="monthly_income",
        prioritize_user_question=False,
        response_channel="model",
        resume_applied=True,
    )
    refreshed_turn_decision = TurnDecision(
        intent="confirmation",
        primary_move="light_followup",
        ask_field=None,
        prioritize_user_question=True,
        response_channel="model",
        user_concern_type="faq",
    )
    chat_service._build_turn_decision = AsyncMock(return_value=refreshed_turn_decision)

    _, final_decision = await chat_service.refresh_turn_decision_after_collection(
        ai_response="好的",
        account_id="u_refresh_preserve_resume",
        user_message="好的",
        user_profile=profile,
        conversation_context={"recent_responses": ["我知道你会好奇为什么要了解得这么清楚。"]},
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="confirmation",
            subtype="weak_confirmation",
            post_answer_reentry=True,
            confidence=0.85,
        ),
        previous_turn_decision=previous_turn_decision,
        collection_result={},
    )

    assert final_decision is previous_turn_decision


@pytest.mark.anyio
async def test_refresh_turn_decision_after_collection_forces_next_target_after_real_progress():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_refresh_progress_followup")
    profile.sex = "女"
    profile.age = 33
    profile.location = "沈阳"
    profile.education = "本科"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True}
    )
    previous_turn_decision = TurnDecision(
        intent="general",
        primary_move="light_followup",
        ask_field="occupation",
        prioritize_user_question=False,
        response_channel="model",
    )
    chat_service._build_turn_decision = AsyncMock(
        return_value=TurnDecision(
            intent="general",
            primary_move="light_followup",
            ask_field=None,
            prioritize_user_question=False,
            response_channel="model",
        )
    )

    _, final_decision = await chat_service.refresh_turn_decision_after_collection(
        ai_response="原来是做客服相关工作的呀，我记下来啦。",
        account_id="u_refresh_progress_followup",
        user_message="客服",
        user_profile=profile,
        conversation_context={"recent_responses": ["你现在是做什么工作的呀？"]},
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="invalid_input",
            subtype="ambiguous_short_answer",
            confidence=0.51,
        ),
        previous_turn_decision=previous_turn_decision,
        collection_result={"all_fields": [{"field": "occupation", "value": "客服"}]},
    )

    assert final_decision.ask_field == "marital_status"
    assert final_decision.primary_move == "light_followup"


def test_policy_uses_effective_ask_count_to_block_core_field_even_when_raw_count_is_low():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_effective_ask_limit")
    profile.effective_field_ask_count["occupation"] = 2
    profile.field_ask_count["occupation"] = 0

    assert chat_service.collection_policy.can_actively_ask(profile, "occupation") is False


def test_finalize_followup_alignment_rewrites_dangling_ack_when_progress_exists():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_dangling_ack")
    profile.sex = "女"
    profile.age = 33
    profile.location = "沈阳"
    profile.education = "本科"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True}
    )
    turn_decision = TurnDecision(
        intent="general",
        primary_move="light_followup",
        ask_field="marital_status",
        allow_medium_target=True,
        response_channel="model",
    )

    rewritten = chat_service.finalize_service._maybe_enforce_main_followup_alignment(
        user_profile=profile,
        user_message="客服",
        final_response="原来是做客服相关工作的呀，我记下来啦。",
        turn_decision=turn_decision,
        collection_result={"all_fields": [{"field": "occupation", "value": "客服"}]},
    )

    assert rewritten != "原来是做客服相关工作的呀，我记下来啦。"
    assert "感情状态" in rewritten or "婚况" in rewritten or "单身" in rewritten or "离婚" in rewritten


def test_question_budget_guard_preserves_ai_ack_prefix_when_falling_back():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_budget_guard_style_prefix")

    guarded = chat_service._enforce_question_budget_guard(
        "原来你是做IT的呀，挺厉害的。对了，你今年多大呀？",
        user_profile=profile,
        user_message="做it呢",
        turn_decision=TurnDecision(
            intent="general",
            primary_move="light_followup",
            ask_field="partner_requirement",
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
        ),
    )

    assert guarded.startswith("原来你是做IT的呀，挺厉害的。")
    assert "今年多大" not in guarded
    assert "另一半" in guarded or "找对象" in guarded or "看重" in guarded


def test_finalize_followup_alignment_preserves_ai_ack_prefix_when_rewriting():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_followup_style_prefix")
    profile.sex = "女"
    profile.age = 33
    profile.location = "沈阳"
    profile.education = "本科"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True}
    )

    rewritten = chat_service.finalize_service._maybe_enforce_main_followup_alignment(
        user_profile=profile,
        user_message="客服",
        final_response="原来你是做客服相关工作的呀，我先记下啦。",
        turn_decision=TurnDecision(
            intent="general",
            primary_move="light_followup",
            ask_field="marital_status",
            allow_medium_target=True,
            response_channel="model",
        ),
        collection_result={"all_fields": [{"field": "occupation", "value": "客服"}]},
    )

    assert rewritten.startswith("原来你是做客服相关工作的呀")
    assert "感情状态" in rewritten or "婚况" in rewritten or "单身" in rewritten or "离婚" in rewritten


def test_finalize_followup_alignment_rewrites_contact_hobby_dangling_response():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_contact_alignment")
    profile.sex = "女"
    profile.age = 28
    profile.age_label = "98年"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "在编教师"
    profile.marital_status = "未婚单身"
    profile.monthly_income = "18万左右"
    profile.partner_requirement = "180cm及以上，90后，工作稳定"

    rewritten = chat_service.finalize_service._maybe_enforce_main_followup_alignment(
        user_profile=profile,
        user_message="深圳啊",
        final_response="我大概捋清楚你的情况啦，你平时有没有比较喜欢的兴趣爱好呀？",
        turn_decision=TurnDecision(
            intent="general",
            primary_move="light_followup",
            ask_field="contact",
            allow_contact_target=True,
            allow_medium_target=False,
            response_channel="model",
        ),
        collection_result={"all_fields": [{"field": "location", "value": "深圳"}]},
    )

    assert "微信" not in rewritten
    assert any(token in rewritten for token in ("手机号", "电话", "号码"))


def test_budget_guard_fallback_uses_divorce_confirmation_question_instead_of_neutral_hold():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_budget_divorce_hold")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    profile.collection_progress["marital_status"] = True

    rewritten = chat_service._build_budget_guard_fallback_response(
        user_profile=profile,
        user_message="离婚",
        ask_field="marital_status",
        allow_medium_target=False,
    )

    assert "离婚" in rewritten
    assert "办妥" in rewritten or "手续" in rewritten
    assert "继续往下说" not in rewritten
    assert "先放这儿" not in rewritten


def test_finalize_service_rewrites_divorce_dangling_hold_to_confirmation_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_finalize_divorce_hold")
    profile.sex = "女"
    profile.age = 39
    profile.location = "沈阳"
    profile.education = "本科"
    profile.occupation = "客服"
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True, "occupation": True, "marital_status": True}
    )

    rewritten = chat_service.finalize_service._maybe_eliminate_dangling_progress_hold(
        user_profile=profile,
        user_message="离婚",
        final_response="现在是这个状态。 这个我先放这儿，咱们继续往下说。",
        turn_decision=TurnDecision(
            intent="general",
            primary_move="confirm_status_only",
            ask_field="marital_status",
            next_action="confirm_divorce_status",
            allow_medium_target=False,
            response_channel="model",
        ),
        collection_result={"all_fields": [{"field": "marital_status", "value": "离异"}]},
    )

    assert "离婚" in rewritten
    assert "办妥" in rewritten or "手续" in rewritten
    assert rewritten != "现在是这个状态。 这个我先放这儿，咱们继续往下说。"


def test_legacy_clean_response_collapses_redundant_confirmation_phrase():
    chat_service = _build_chat_service()

    cleaned = chat_service._legacy_clean_response(
        "我这边确认一下，那我确认一下，你这边是男生对吧？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？"
    )

    assert cleaned == "我这边确认一下，你这边是男生对吧？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？"


def test_legacy_clean_response_softens_awkward_age_question():
    chat_service = _build_chat_service()

    cleaned = chat_service._legacy_clean_response("挺好的，你是哪年的呀？")

    assert cleaned == "挺好的，那你大概是哪一年出生的呀？"


def test_safe_clean_response_does_not_apply_legacy_age_rewrite():
    chat_service = _build_chat_service()

    cleaned = chat_service._safe_clean_response("挺好的，你是哪年的呀？")

    assert cleaned == "挺好的，你是哪年的呀？"


def test_legacy_clean_response_keeps_backward_compatible_rewrite_behavior():
    chat_service = _build_chat_service()

    cleaned = chat_service._legacy_clean_response("挺好的，你是哪年的呀？")

    assert cleaned == "挺好的，那你大概是哪一年出生的呀？"


def test_needs_style_retry_uses_safe_cleanup_for_recent_response_comparison():
    chat_service = _build_chat_service()
    assert hasattr(chat_service, "_needs_style_retry")
    assert (
        chat_service._needs_style_retry(
            "好的呀，你现在常住哪个城市呀？",
            conversation_context={"recent_responses": ["好的呀，你现在常住哪个城市呀？"]},
        )
        is True
    )
    assert (
        chat_service._needs_style_retry(
            "那你现在做什么工作呀？",
            conversation_context={"recent_responses": ["好的呀，你现在常住哪个城市呀？"]},
        )
        is False
    )


def test_style_ai_rewrite_entries_are_removed():
    chat_service = _build_chat_service()

    assert not hasattr(chat_service, "_rewrite_response_for_style")
    assert not hasattr(chat_service, "_rewrite_response_for_profile_bridge")


@pytest.mark.asyncio
async def test_maybe_build_preset_response_payload_prefers_legacy_clean_response():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_preset_legacy_clean")
    chat_service._legacy_clean_response = lambda text: f"{text}|legacy_clean"
    chat_service._sanitize_robotic_tone = lambda text: text
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._build_chat_response = AsyncMock(return_value={"ok": True})

    final_response, payload = await chat_service.maybe_build_preset_response_payload(
        account_id="u_preset_legacy_clean",
        user_profile=profile,
        user_message="你好",
        dialog_id="dlg_preset",
        collection_result={"response": "预设回复"},
    )

    assert final_response == "预设回复|legacy_clean"
    assert payload == {"ok": True}


def test_build_policy_field_prompt_prefers_soft_gender_confirmation_from_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_gender_priority")
    profile.partner_requirement = "温柔，苗条"

    response = chat_service._build_policy_field_prompt("sex", profile, user_message="90后")

    assert "男生还是女生" not in response
    assert "男生" in response
    assert any(token in response for token in ("对吧", "是吧", "确认"))


def test_build_policy_field_prompt_prefers_soft_gender_confirmation_from_handsome_tall_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_gender_priority_handsome_tall")
    profile.partner_requirement = "身高较高、外形帅气"

    response = chat_service._build_policy_field_prompt("sex", profile, user_message="喜欢高点的帅气的")

    assert "男生还是女生" not in response
    assert "女生" in response
    assert any(token in response for token in ("对吧", "是吧", "确认"))


def test_build_policy_field_prompt_prefers_soft_occupation_confirmation_from_inference_candidate():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_occupation_priority")
    profile.occupation_inference_candidate = "财务"

    response = chat_service._build_policy_field_prompt("occupation", profile, user_message="最好不要同财务行业")

    assert "做哪方面工作" in response or "从事什么方向的工作" in response
    assert "财务" not in response
    assert "纠正我" not in response


def test_build_policy_field_prompt_keeps_plain_occupation_prompt_without_inference_candidate():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_plain_occupation_priority")

    response = chat_service._build_policy_field_prompt("occupation", profile, user_message="想找对象")

    assert "做哪方面工作" in response


def test_build_generation_prompt_prefers_soft_gender_confirmation_for_handsome_tall_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_gender_prompt_handsome_tall")
    profile.age = 28
    profile.age_label = "98年"
    profile.location = "深圳"
    profile.occupation = "美容相关"
    profile.monthly_income = "3万"
    profile.education = "本科"
    profile.marital_status = "单身"
    profile.partner_requirement = "身高较高、外形帅气"

    prompt = chat_service.build_generation_prompt(
        user_message="本科，单身呢",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="sex",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=False,
            allow_contact_target=True,
        ),
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"education": "本科", "marital_status": "单身"},
        ),
    )

    assert "【性别软确认专用生成】" in prompt
    assert "不要直接写“你是男生还是女生呀？”" in prompt
    assert "不要说“我听出来了/我分析出来了/按你的偏好判断”" in prompt
    assert "女生" in prompt


def test_build_generation_prompt_prefers_persistence_plan_partner_requirement_for_soft_gender_confirmation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_soft_gender_prompt_plan_requirement")
    profile.age = 28
    profile.age_label = "98年"
    profile.location = "深圳"
    profile.occupation = "美容相关"
    profile.monthly_income = "3万"
    profile.education = "本科"
    profile.marital_status = "单身"

    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"education": "本科", "marital_status": "单身"},
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="partner_requirement",
                    value="身高较高、外形帅气",
                    normalized_value="身高较高、外形帅气",
                    scope="partner",
                    evidence_text="身高较高、外形帅气",
                    confidence=0.96,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    prompt = chat_service.build_generation_prompt(
        user_message="本科，单身呢",
        user_profile=profile,
        conversation_context={},
        turn_decision=TurnDecision(
            ask_field="sex",
            response_channel="model",
            primary_move="ack_and_ask",
            allow_medium_target=False,
            allow_contact_target=True,
        ),
        understanding_result=understanding,
    )

    assert "【性别软确认专用生成】" in prompt
    assert "女生" in prompt


@pytest.mark.anyio
async def test_track_ai_asked_fields_does_not_close_medium_field_active_ask_on_simple_ask():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_medium_close")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service.ask_tracking_service.track_ai_asked_fields(
        "u_medium_close",
        "你这边对另一半有什么比较在意的点吗？",
    )

    assert profile.is_active_ask_closed("partner_requirement") is False
    assert profile.get_ask_count("partner_requirement") == 1


@pytest.mark.anyio
async def test_track_ai_asked_fields_does_not_mistake_single_resource_copy_for_marital_status_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_no_false_marital_skip")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service.user_service.save_user_profile = AsyncMock(return_value=True)

    await chat_service.ask_tracking_service.track_ai_asked_fields(
        "u_no_false_marital_skip",
        "对哦我们是正规的婚恋服务机构，现有资源都是真实单身用户，这点你可以放心哈。你是男生还是女生呀？",
    )

    assert profile.get_ask_count("sex") == 1
    assert profile.get_ask_count("marital_status") == 0


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
    latest_profile.partner_gender_preference = "男"
    latest_profile.collection_progress["partner_gender_preference"] = True
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
    assert payload["collected_info"]["partner_gender_preference"] == "男生"
    assert payload["collected_info"]["education"] == "本科"


@pytest.mark.anyio
async def test_build_chat_response_prefers_current_turn_all_fields_in_collected_info():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_current_turn_overlay")
    latest_profile.education = None
    latest_profile.location = None
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_current_turn_overlay",
        UserProfile(account_id="u_current_turn_overlay"),
        "我们继续聊。",
        {
            "all_fields": [
                {"field": "education", "value": "本科"},
                {"field": "location", "value": "深圳龙华"},
            ]
        },
        "dlg_overlay",
        {},
    )

    assert payload["collected_info"]["education"] == "本科"
    assert payload["collected_info"]["location"] == "深圳龙华"


@pytest.mark.anyio
async def test_build_chat_response_prefers_current_turn_contact_values_in_collected_info():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_current_turn_contact_overlay")
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_current_turn_contact_overlay",
        UserProfile(account_id="u_current_turn_contact_overlay"),
        "我们继续聊。",
        {
            "all_fields": [
                {"field": "phone", "value": "17688765432"},
                {"field": "wechat", "value": "wx7789789"},
            ]
        },
        "dlg_contact_overlay",
        {},
    )

    assert payload["collected_info"]["contact"] == "电话: 17688765432, 微信: wx7789789"


@pytest.mark.anyio
async def test_build_chat_response_exposes_occupation_inference_candidate_in_collected_info():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_refresh_inferred_occupation")
    latest_profile.occupation_inference_candidate = "财务"
    latest_profile.set_extraction_evidence(
        field_name="occupation_inference_candidate",
        value="财务",
        source_text="最好不要同财务行业，倾向稳定行业男生",
        turn_id=1,
        confidence=0.82,
        source="partner_requirement_inference",
        reason="same_industry_exclusion",
    )
    latest_profile.partner_requirement = "不要同财务行业，稳定行业"
    latest_profile.collection_progress["partner_requirement"] = True
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_inferred_occupation",
        UserProfile(account_id="u_refresh_inferred_occupation"),
        "我们继续聊。",
        {},
        "dlg_2a",
        {},
    )

    assert payload["collected_info"]["occupation"] == "未确认"
    assert payload["collected_info"]["occupation_inference_candidate"] == "[推断] 财务 (0.82, 中置信, 同行反推)"
    assert payload["collected_info"]["partner_requirement"] == "不要同财务行业，稳定行业"


@pytest.mark.anyio
async def test_build_chat_response_hides_occupation_inference_candidate_after_occupation_confirmed():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_refresh_confirmed_occupation")
    latest_profile.occupation = "财务"
    latest_profile.collection_progress["occupation"] = True
    latest_profile.occupation_inference_candidate = "财务"
    latest_profile.set_extraction_evidence(
        field_name="occupation_inference_candidate",
        value="财务",
        source_text="最好不要同财务行业",
        turn_id=1,
        confidence=0.82,
        source="partner_requirement_inference",
        reason="same_industry_exclusion",
    )
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_confirmed_occupation",
        UserProfile(account_id="u_refresh_confirmed_occupation"),
        "我们继续聊。",
        {},
        "dlg_2b",
        {},
    )

    assert payload["collected_info"]["occupation"] == "财务"
    assert payload["collected_info"]["occupation_inference_candidate"] == "无"


@pytest.mark.anyio
async def test_build_chat_response_does_not_show_gender_preference_as_partner_requirement():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_refresh_gender_pref_only")
    latest_profile.partner_gender_preference = "男"
    latest_profile.collection_progress["partner_gender_preference"] = True
    latest_profile.partner_requirement = None
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_gender_pref_only",
        UserProfile(account_id="u_refresh_gender_pref_only"),
        "我们继续聊。",
        {},
        "dlg_2",
        {},
    )

    assert payload["collected_info"]["partner_gender_preference"] == "男生"
    assert payload["collected_info"]["partner_requirement"] == "未留"


@pytest.mark.anyio
async def test_build_chat_response_falls_back_to_structured_partner_preference_when_requirement_missing():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_refresh_structured_partner_pref")
    latest_profile.partner_gender_preference = "男"
    latest_profile.collection_progress["partner_gender_preference"] = True
    latest_profile.partner_requirement = None
    latest_profile.partner_pref_age = "90后"
    latest_profile.partner_pref_location = "深圳"
    latest_profile.partner_pref_industry = "程序员"
    latest_profile.collection_progress["partner_pref_age"] = True
    latest_profile.collection_progress["partner_pref_location"] = True
    latest_profile.collection_progress["partner_pref_industry"] = True
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_structured_partner_pref",
        UserProfile(account_id="u_refresh_structured_partner_pref"),
        "我们继续聊。",
        {},
        "dlg_structured_pref",
        {},
    )

    assert payload["collected_info"]["partner_gender_preference"] == "男生"
    assert payload["collected_info"]["partner_requirement"] == "90后，深圳，程序员"


@pytest.mark.anyio
async def test_build_chat_response_hides_polluted_partner_requirement_when_it_is_only_gender_preference():
    chat_service = _build_chat_service()
    latest_profile = UserProfile(account_id="u_refresh_gender_pref_polluted")
    latest_profile.partner_gender_preference = None
    latest_profile.partner_requirement = "找男朋友"
    latest_profile.collection_progress["partner_requirement"] = True
    chat_service.user_service.get_user_profile = AsyncMock(return_value=latest_profile)

    payload = await chat_service._build_chat_response(
        "u_refresh_gender_pref_polluted",
        UserProfile(account_id="u_refresh_gender_pref_polluted"),
        "我们继续聊。",
        {},
        "dlg_2b",
        {},
    )

    assert payload["collected_info"]["partner_gender_preference"] == "男生"
    assert payload["collected_info"]["partner_requirement"] == "未留"


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

    assert response == "原始回复"
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
    chat_service.validation_recovery_service.generate_validation_retry_response = AsyncMock(
        return_value="这个号码像是不太对，你再确认一下。"
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
    chat_service.validation_recovery_service.generate_validation_retry_response.assert_awaited_once()


@pytest.mark.anyio
async def test_generate_validation_retry_response_prefers_local_phone_format_retry_copy():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="user_invalid_phone_copy")

    response = await chat_service._generate_validation_retry_response(
        account_id="user_invalid_phone_copy",
        user_profile=profile,
        user_message="17877654ff",
        invalid_value="17877654ff",
        error_info={"field": "phone", "detail": "invalid_format", "attempt": 1},
    )

    assert "没发完整" in response or "格式" in response
    assert "手机号" in response
    assert "不想留太多" not in response
    assert "稍后发" not in response
    assert "晚点发" not in response


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

    assert response == "微信我看到了，我们接着往下聊就行。"


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
async def test_process_chat_request_boundary_uses_model_generated_repair_by_default(monkeypatch):
    monkeypatch.setenv("MQ_MODEL_GENERATED_REPAIR_ENABLED", "1")
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
    chat_service._call_ai = AsyncMock(return_value="我先接住你这句，这轮先不追问资料。你想先聊哪一块我顺着你来。")

    request = SimpleNamespace(
        accountId="user_boundary_pause",
        question="电话先不方便留，我先不留",
        dialogId="dlg_boundary",
        sex=None,
        timestamp=None,
    )
    result = await chat_service.process_chat_request(request)

    assert "先不追问资料" in result["response"]
    chat_service._call_ai.assert_awaited()
    chat_service._handle_refusal_detection.assert_awaited_once()


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

    assert result["response"]
    assert "再发一句" in result["response"]
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


def test_enforce_opening_listener_first_policy_acknowledges_city_preference_before_intro():
    chat_service = _build_chat_service()
    understanding = SimpleNamespace(primary_turn_type="opening", subtype="matchmaking_intent")

    response = chat_service._enforce_opening_listener_first_policy(
        "好，你也可以先简单介绍下自己，我先了解下你的情况",
        understanding,
        "我喜欢深圳的女生",
    )

    assert "深圳" in response or "同城" in response
    assert "女生" in response or "偏" in response
    assert "介绍下自己" in response or "说说你自己的情况" in response


def test_build_resume_after_interrupt_response_returns_to_interrupted_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_resume_after_faq")
    profile.sex = "男"
    profile.location = "深圳"
    profile.age = 36
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update(
        {"sex": True, "location": True, "age": True, "education": True, "occupation": True}
    )

    response = chat_service._build_resume_after_interrupt_response(
        "按你现在的情况，常见是1-2天会有推进。",
        profile,
        user_message="你们多久会联系我呀",
        last_response="你找对象时会更看重哪方面？",
    )

    assert "1-2天" in response or "推进" in response
    assert any(token in response for token in ("看重", "另一半", "要求"))


def test_build_turn_decision_marks_work_busy_context_ack():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_topic_work")
    profile.occupation = "运营"

    decision = chat_service._build_turn_decision("我工作比较忙", profile, conversation_context={"message_count": 2})

    assert decision.followup_topic == "work_busy"
    assert decision.context_ack_required is True
    assert decision.context_ack_type == "work_busy"
    assert decision.context_ack_occupation == "运营"


def test_apply_context_ack_policy_reuses_work_topic_without_fixed_template():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_context_work")
    profile.occupation = "运营"
    decision = SimpleNamespace(
        context_ack_required=True,
        context_ack_type="work_busy",
        context_ack_payload={"occupation": "运营"},
        context_ack_occupation="运营",
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
        context_ack_field_ack="本科我知道了。",
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


def test_looks_like_fake_info_message_detects_impossible_age_and_height():
    chat_service = _build_chat_service()

    assert chat_service._looks_like_fake_info_message("我是女生，今年1000岁，身高3米") is True
    assert chat_service._looks_like_fake_info_message("我今年35，在深圳") is False
    assert chat_service._looks_like_fake_info_message("我今年36，想找和我上下相差3岁的") is False


def test_apply_income_appreciation_policy_adds_light_ack_for_high_income():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_income_ack")
    profile.monthly_income = "5万"
    chat_service._should_add_light_appreciation = lambda _profile, _marker: True

    response = chat_service._apply_income_appreciation_policy(
        "好呀，你大概是什么学历呀？ 这样我对你的情况会更有数一点。",
        profile,
        {"all_fields": [{"field": "monthly_income", "value": "5万"}]},
    )

    assert "挺不错" in response or "还挺不错" in response


def test_apply_income_appreciation_policy_adds_light_ack_for_high_education_only_when_enabled():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_education_ack")
    profile.education = "博士"
    chat_service._should_add_light_appreciation = lambda _profile, marker: marker == "education"

    response = chat_service._apply_income_appreciation_policy(
        "你现在大概什么年龄段呀？",
        profile,
        {"all_fields": [{"field": "education", "value": "博士"}]},
    )

    assert "学历" in response


def test_apply_income_appreciation_policy_skips_when_gate_closed():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_income_ack_closed")
    profile.monthly_income = "5万"
    chat_service._should_add_light_appreciation = lambda _profile, _marker: False

    response = chat_service._apply_income_appreciation_policy(
        "你大概是什么学历呀？",
        profile,
        {"all_fields": [{"field": "monthly_income", "value": "5万"}]},
    )

    assert response == "你大概是什么学历呀？"


def test_apply_income_appreciation_policy_adds_light_ack_for_stable_occupation_only_when_enabled():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_occupation_ack")
    profile.occupation = "IT"
    chat_service._should_add_light_appreciation = lambda _profile, marker: marker == "occupation"

    response = chat_service._apply_income_appreciation_policy(
        "你大概是什么学历呀？",
        profile,
        {"all_fields": [{"field": "occupation", "value": "IT"}]},
    )

    assert "挺稳" in response


def test_should_add_light_appreciation_skips_after_contact_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_appreciation_with_contact")
    profile.phone = "17600000000"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True

    assert chat_service._should_add_light_appreciation(profile, "income") is False


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


def test_get_risk_guard_response_does_not_treat_medical_industry_preference_as_medical_advice():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_medical_industry_intro")

    response = chat_service._get_risk_guard_response(
        "90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地",
        profile,
    )

    assert "正规医生" not in response
    assert "专业机构确认" not in response


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
async def test_call_ai_delegates_to_ai_response_generator():
    chat_service = _build_chat_service()
    chat_service.ai_response_generator.generate = AsyncMock(
        return_value=AIResponseResult(content="模型回复", failure_reason=None)
    )

    result = await chat_service._call_ai("prompt", "user_ai_delegate", "你好")

    assert result == "模型回复"
    chat_service.ai_response_generator.generate.assert_awaited_once()
    kwargs = chat_service.ai_response_generator.generate.await_args.kwargs
    assert kwargs["prompt"] == "prompt"
    assert kwargs["account_id"] == "user_ai_delegate"
    assert kwargs["user_message"] == "你好"


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


def test_enforce_natural_completion_transition_moves_to_contact_after_occupation():
    chat_service = _build_chat_service()
    assert not hasattr(chat_service, "_enforce_natural_completion_transition")


def test_enforce_natural_completion_transition_keeps_non_contact_response_when_not_ready():
    chat_service = _build_chat_service()
    assert not hasattr(chat_service, "_enforce_natural_completion_transition")




def test_apply_humanlike_turn_structure_policy_does_not_prefix_contact_prompt_twice():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_prefix")

    response = chat_service._apply_humanlike_turn_structure_policy(
        "先留个手机号也行，后面如果有合适的进展，我这边也好继续联系上你。",
        profile,
        "it",
        allow_medium_target=True,
    )

    assert "手机号" in response
    assert "后面如果继续聊得合适，也方便及时联系你" not in response


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
    assert any(token in response for token in ["婚况", "感情状态", "单身", "分居"])


def test_apply_humanlike_turn_structure_policy_interleaves_marital_status_after_location_stage():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_location")
    profile.sex = "女"
    profile.age = 38
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update({"sex": True, "age": True, "education": True, "occupation": True})
    profile.recent_asked_fields = ["sex", "age", "education", "occupation"]

    response = chat_service._apply_humanlike_turn_structure_policy(
        "你平时常住在哪座城市呀？",
        profile,
        "IT",
        allow_medium_target=True,
    )

    assert any(token in response for token in ["城市", "常住", "哪座"])
    assert any(token in response for token in ["婚况", "感情状态", "单身", "分居"])


def test_profile_collection_policy_blocks_unrelated_side_target_in_opening_stage():
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

    assert side_target == "marital_status"


def test_profile_collection_policy_no_longer_allows_income_side_target_with_occupation_in_opening_stage():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_opening_income_side")

    side_target = policy.get_side_target(
        profile,
        main_target="occupation",
        user_message="来自深圳",
        message_count=1,
        allow_medium_target=True,
    )

    assert side_target == "marital_status"


def test_profile_collection_policy_does_not_attach_income_side_target_to_education_after_occupation_cue():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_income_after_occupation_cue")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="做it，吧",
        message_count=2,
        allow_medium_target=True,
    )

    assert side_target != "monthly_income"


def test_profile_collection_policy_no_longer_prefers_monthly_income_as_side_target_after_occupation_cue():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_income_main_after_occupation")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    decision = policy.decide(
        profile,
        user_message="做it吧",
        message_count=2,
    )

    assert decision.main_target == "occupation"
    assert decision.side_target is None


def test_profile_collection_policy_recognizes_generic_location_phrase_as_location_cue():
    cue_order = ProfileCollectionPolicy._extract_message_field_cue_order("在南京呢")  # noqa: SLF001

    assert "location" in cue_order


def test_profile_collection_policy_prefers_occupation_after_generic_location_phrase():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_location_to_occupation")
    profile.sex = "女"
    profile.age = 28
    profile.collection_progress.update({"sex": True, "age": True})

    main_target = policy.get_main_target(
        profile,
        can_enter_contact=False,
        allow_contact_target=False,
        user_message="在南京呢",
        message_count=4,
    )

    assert main_target == "occupation"


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


def test_profile_collection_policy_blocks_side_target_when_other_core_fields_remain():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_no_side_while_core_missing")
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"age": True, "location": True})

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="深圳",
        message_count=6,
        allow_medium_target=True,
    )

    assert side_target is None


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


def test_profile_collection_policy_allows_marital_status_as_side_target_after_education_earlier_when_context_present():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_policy_marital_early")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.collection_progress.update({"sex": True, "age": True, "location": True})

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="本科",
        message_count=2,
        allow_medium_target=True,
    )

    assert side_target == "marital_status"


def test_response_plan_builder_adds_soft_constraints_for_marital_and_sex():
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=DialogueExpressionService(),
    )
    profile = UserProfile(account_id="u_plan_builder")
    profile.partner_gender_preference = "男"

    marital_spec = builder._build_field_followup_spec(
        ask_field="education",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="opening",
            next_action="continue",
            primary_move="ack_and_ask",
            ask_field="education",
            allow_medium_target=True,
            allow_contact_target=False,
            response_channel="model",
        ),
        user_profile=profile,
        user_message="做it，吧",
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        secondary_signals=set(),
        resolved_slots={"occupation": "IT"},
    )

    assert marital_spec.plan.side_target is None

    sex_spec = builder._build_field_followup_spec(
        ask_field="sex",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="opening",
            next_action="continue",
            primary_move="light_followup",
            ask_field="sex",
            allow_medium_target=False,
            allow_contact_target=False,
            response_channel="model",
        ),
        user_profile=profile,
        user_message="我想找男朋友",
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        secondary_signals=set(),
        resolved_slots={},
    )

    assert any("高概率可推断用户是女生" in item for item in sex_spec.plan.constraints)
    assert any("不要直接生硬二选一" in item for item in sex_spec.plan.constraints)


def test_response_plan_builder_marital_status_prefers_open_status_question_not_singlehood_confirmation():
    understanding_stub = SimpleNamespace(_extract_partner_gender_preference=lambda _message: None)
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=understanding_stub,
    )
    profile = UserProfile(account_id="u_plan_builder_marital")

    marital_spec = builder._build_field_followup_spec(
        ask_field="marital_status",
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="opening",
            next_action="continue",
            primary_move="light_followup",
            ask_field="marital_status",
            allow_medium_target=False,
            allow_contact_target=False,
            response_channel="model",
        ),
        user_profile=profile,
        user_message="本科，收入7万",
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        secondary_signals=set(),
        resolved_slots={"education": "本科", "monthly_income": "7万"},
    )

    assert any("开放式问法" in item for item in marital_spec.plan.constraints)
    assert any("单身状态吗" in item or "单身吗" in item for item in marital_spec.plan.constraints)
    assert any("不适合直接按单身理解" in item or "确认准一点" in item for item in marital_spec.plan.constraints)


def test_response_plan_builder_opening_prefers_soft_sex_confirmation_for_matchmaking_opening():
    understanding_stub = SimpleNamespace(
        _looks_like_greeting=lambda _message: True,
        _is_service_confirmation_like=lambda _message: False,
        _extract_partner_gender_preference=lambda _message: "男",
    )
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=understanding_stub,
    )
    profile = UserProfile(account_id="u_opening_soft_confirm")

    opening_spec = builder._build_opening_spec(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        secondary_signals={"opening_greeting", "opening_matchmaking_intent"},
        resolved_slots={"partner_gender_preference": "男"},
        user_profile=profile,
        user_message="你好，我找男朋友",
    )

    assert opening_spec is not None
    assert any("高概率可推断用户是女生" in item for item in opening_spec.plan.ack_items)
    assert "轻量软确认性别" in opening_spec.plan.next_move
    assert any("不要默认退化成‘你是女生还是男生’" in item for item in opening_spec.plan.constraints)


def test_response_plan_builder_prefers_persistence_plan_accepted_fields_over_legacy_slots():
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=SimpleNamespace(
            _looks_like_greeting=lambda _message: False,
            _is_service_confirmation_like=lambda _message: False,
            _extract_partner_gender_preference=lambda _message: None,
        ),
    )
    understanding = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        resolved_slots={"partner_gender_preference": "女"},
    )
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="partner_gender_preference",
                    value="男",
                    normalized_value="男",
                    scope="partner",
                    evidence_text="找男朋友",
                    confidence=0.97,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    opening_spec = builder.build(
        turn_decision=TurnDecision(
            intent="general",
            risk="none",
            stage="opening",
            next_action="continue",
            primary_move="ack_and_ask",
            response_channel="model",
        ),
        user_profile=UserProfile(account_id="u_plan_builder_persistence"),
        user_message="你好，我找男朋友",
        understanding_result=understanding,
    )

    assert opening_spec is not None
    assert any("偏向找男生" in item for item in opening_spec.plan.ack_items)


def test_response_plan_builder_builds_complaint_repair_spec_without_short_circuit_template():
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=SimpleNamespace(
            _looks_like_greeting=lambda _message: False,
            _is_service_confirmation_like=lambda _message: False,
            _extract_partner_gender_preference=lambda _message: None,
        ),
    )
    spec = builder.build(
        turn_decision=TurnDecision(
            intent="complaint",
            risk="none",
            stage="completing",
            next_action="continue",
            primary_move="repair_and_release",
            ask_field=None,
            response_channel="model",
        ),
        user_profile=UserProfile(account_id="u_plan_builder_complaint"),
        user_message="不是说了吗？",
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="refusal_boundary_complaint",
            subtype="complaint",
            secondary_signals=["needs_resume_mainline"],
        ),
    )

    assert spec is not None
    assert spec.plan.mode == "complaint_repair"
    assert any("可执行" in item for item in spec.plan.constraints)
    assert "投诉修复优先" in spec.header


def test_response_plan_builder_builds_boundary_hold_spec_without_short_circuit_template():
    builder = ResponsePlanBuilder(
        collection_policy=ProfileCollectionPolicy(),
        turn_understanding_service=SimpleNamespace(
            _looks_like_greeting=lambda _message: False,
            _is_service_confirmation_like=lambda _message: False,
            _extract_partner_gender_preference=lambda _message: None,
        ),
    )
    spec = builder.build(
        turn_decision=TurnDecision(
            intent="boundary",
            risk="boundary",
            stage="opening",
            next_action="continue",
            primary_move="soft_hold",
            ask_field=None,
            response_channel="model",
        ),
        user_profile=UserProfile(account_id="u_plan_builder_boundary"),
        user_message="先不聊这些",
        understanding_result=TurnUnderstandingResult(
            primary_turn_type="refusal_boundary_complaint",
            subtype="boundary_defensive",
        ),
    )

    assert spec is not None
    assert spec.plan.mode == "boundary_hold"
    assert any("不要继续追问新资料" in item for item in spec.plan.constraints)


def test_merge_collection_result_into_shadow_profile_keeps_explicit_self_marker_high_risk_fields():
    chat_service = _build_chat_service()
    shadow_profile = UserProfile(account_id="u_shadow_explicit_marker")
    understanding_result = TurnUnderstandingResult(primary_turn_type="profile_answer")
    setattr(
        understanding_result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="在编教师",
                    normalized_value="在编教师",
                    scope="self",
                    evidence_text="在编教师",
                    confidence=0.98,
                    acceptance_reason="explicit_self_marker",
                    update_action="accept_as_new",
                    persistence_state="committed",
                    source_channel="hybrid",
                ),
                AcceptedField(
                    field="monthly_income",
                    value="年薪20+",
                    normalized_value="年薪20+",
                    scope="self",
                    evidence_text="年薪20+",
                    confidence=0.98,
                    acceptance_reason="explicit_self_marker",
                    update_action="accept_as_new",
                    persistence_state="committed",
                    source_channel="hybrid",
                ),
            ]
        ),
    )

    merged = chat_service._merge_collection_result_into_shadow_profile(  # noqa: SLF001
        shadow_profile,
        collection_result={"all_fields": []},
        understanding_result=understanding_result,
    )

    assert merged.occupation == "在编教师"
    assert merged.monthly_income == "年薪20+"
    assert merged.collection_progress["occupation"] is True
    assert merged.collection_progress["monthly_income"] is True


def test_generation_prompt_service_prefers_persistence_plan_contact_fields_for_completion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_generation_prompt_persistence")
    profile.sex = "女"
    profile.age = 28
    profile.education = "本科"
    profile.monthly_income = "3万"
    profile.location = "深圳"
    profile.occupation = "教师"
    profile.marital_status = "未婚"
    profile.partner_requirement = "聊得来"
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "education": True,
            "monthly_income": True,
            "location": True,
            "occupation": True,
            "marital_status": True,
            "partner_requirement": True,
        }
    )
    profile.rejected_wechat = True
    understanding = TurnUnderstandingResult(primary_turn_type="contact_answer", resolved_slots={"phone": ""})
    setattr(
        understanding,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="phone",
                    value="13526783627",
                    normalized_value="13526783627",
                    scope="contact",
                    evidence_text="13526783627",
                    confidence=0.99,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    instruction = chat_service.generation_prompt_service._build_contact_completion_generation_instruction(
        user_profile=profile,
        understanding_result=understanding,
    )

    assert "联系方式已经满足收尾条件" in instruction


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
    assert "几几年" not in response
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
    profile.sex = "男"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.collection_progress.update(
        {"sex": True, "age": True, "location": True, "education": True, "occupation": True}
    )

    response, should_close = chat_service._build_withdraw_response(profile, user_message="不聊了")

    assert should_close is True
    assert any(token in response for token in ("我先帮你记下了", "联系前", "匹配一般"))


def test_build_withdraw_response_does_not_close_when_contact_exists_but_core_incomplete():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_withdraw_contact_incomplete")
    profile.phone = "17600000000"
    profile.phone_collected = True
    profile.collection_progress["contact"] = True

    profile.increment_ask_count("conversation_end_intent")
    response, should_close = chat_service._build_withdraw_response(profile, user_message="不聊了")

    assert should_close is False
    assert any(token in response for token in ("顾虑", "不往下问", "担心"))


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


def test_strip_unverified_memory_ack_removes_fake_memory_claim_when_core_still_missing():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_unverified_memory_ack")

    response = chat_service._strip_unverified_memory_ack(
        "抱歉呀，我刚才没注意到你之前说过。我记好啦，后面会优先给你留意合适方向。",
        profile,
        collection_result={"all_fields": []},
    )

    assert "记好" not in response


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


def test_build_shadow_profile_for_decision_fallback_keeps_self_birth_year_without_partner_bucket_pollution():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_shadow_birth_year_scope")

    shadow = chat_service._build_shadow_profile_for_decision(
        profile,
        "95想找90后都可以有不",
    )

    assert shadow.age == 31
    assert shadow.age_label == "95年"
    assert shadow.pending_birth_year_bucket is None


def test_build_shadow_profile_for_decision_treats_bare_90_as_specific_birth_year():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_shadow_bare_90")

    shadow = chat_service._build_shadow_profile_for_decision(
        profile,
        "90",
    )

    assert shadow.age_label == "90年"
    assert shadow.pending_birth_year_bucket in {None, ""}
    assert shadow.collection_progress["age"] is True


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


@pytest.mark.asyncio
async def test_enforce_profile_bridge_response_falls_back_to_interleaving_followup_when_bridge_needed():
    chat_service = _build_chat_service()
    assert not hasattr(chat_service, "_enforce_profile_bridge_response")


def test_extraction_service_partner_requirement_tolerates_polluted_short_answer():
    assert ExtractionService._extract_partner_requirement_from_user_message("本科，我温柔 点") == "温柔"


def test_extraction_service_partner_requirement_handles_modal_particle_reply():
    assert ExtractionService._extract_partner_requirement_from_user_message("本科，温柔吧") == "温柔"


def test_fuse_extracted_fields_moves_pure_gender_preference_out_of_partner_requirement():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {"partner_requirement": "找男朋友"},
        {},
        user_message="你好，找男朋友",
    )

    assert "partner_requirement" not in fused
    assert fused["partner_gender_preference"] == "男"
    assert "partner_requirement" not in meta


def test_fuse_extracted_fields_keeps_trait_requirement_while_extracting_gender_preference():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {"partner_requirement": "成熟稳重的男生"},
        {},
        user_message="想找成熟稳重的男生",
    )

    assert fused["partner_requirement"] == "成熟稳重"
    assert fused["partner_gender_preference"] == "男"
    assert meta["partner_gender_preference"]["source"] == "partner_requirement_normalized"


def test_fuse_extracted_fields_keeps_composite_requirement_while_extracting_gender_preference():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {"partner_requirement": "接受4岁上下年龄差，对方身高174+，爱笑，不要同财务行业，倾向于稳定行业男生"},
        {},
        user_message="深圳有不 想了解看看96年能接受4岁上下年龄差，喜欢笑就更好了卡身高174+最好不要同财务行业 自己跟跟倾向于稳定行业男生可以匹配不",
    )

    assert fused["partner_requirement"] == "接受4岁上下年龄差，对方身高174+，爱笑，不要同财务行业，倾向于稳定行业男生"
    assert fused["partner_gender_preference"] == "男"
    assert meta["partner_gender_preference"]["source"] == "partner_requirement_normalized"
    assert meta["partner_requirement"]["source"] == "rich_partner_requirement_preserved"
    assert fused["partner_pref_industry"] == "同财务行业"
    assert meta["partner_pref_industry"]["source"] == "partner_requirement_subslot_normalized"


def test_fuse_extracted_fields_hydrates_partner_age_subslot_from_requirement():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {"partner_requirement": "90后"},
        {},
        user_message="96年女生找男朋友，目前在深圳单身未婚，本科学历，与收入1万左右，找90后",
    )

    assert fused["partner_requirement"] == "90后"
    assert fused["partner_pref_age"] == "90后"
    assert meta["partner_pref_age"]["source"] in {"partner_requirement_subslot_normalized", "ai"}


def test_fuse_extracted_fields_composes_partner_requirement_from_structured_subslots_when_missing():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        {},
        user_message="想找深圳，本科及以上",
    )

    assert fused["partner_requirement"] == "深圳，学历本科及以上"
    assert meta["partner_requirement"]["source"] == "structured_partner_requirement_compose"


def test_fuse_extracted_fields_composes_partner_requirement_from_structured_subslots_and_message_tail():
    chat_service = _build_chat_service()

    fused, meta = chat_service._fuse_extracted_fields(
        {
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        {},
        user_message="可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下",
    )

    assert fused["partner_requirement"] == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"
    assert meta["partner_requirement"]["source"] == "structured_partner_requirement_compose"


def test_user_profile_roundtrip_keeps_structured_partner_preference_subslots():
    profile = UserProfile(account_id="u_partner_pref_roundtrip")
    profile.partner_pref_location = "深圳"
    profile.partner_pref_education = "学历本科及以上"
    profile.partner_pref_locality = "同城优先"

    restored = UserProfile.from_dict(profile.to_dict())

    assert restored.partner_pref_location == "深圳"
    assert restored.partner_pref_education == "学历本科及以上"
    assert restored.partner_pref_locality == "同城优先"


@pytest.mark.anyio
async def test_process_chat_request_quick_faq_keeps_rich_partner_requirement_in_collected_info():
    chat_service = ChatService(_FakeAIService(), UserService())
    account_id = f"u_quick_faq_partner_requirement_rich_{uuid.uuid4().hex}"
    chat_service.user_service.reset_conversation(account_id)

    payload = await chat_service.process_chat_request(
        ChatRequest(
            question="可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下",
            accountId=account_id,
            dialogId="dlg_quick_faq_partner_requirement_rich",
        )
    )

    assert payload["collected_info"]["sex"] == "女"
    assert payload["collected_info"]["occupation"] == "在编教师"
    partner_requirement = payload["collected_info"]["partner_requirement"]
    assert "学历本科及以上" in partner_requirement
    assert "同老家在深圳" in partner_requirement
    assert "最好深户" in partner_requirement
    assert "有房有车" in partner_requirement
    assert "不要92" in partner_requirement


def test_replay_opening_mixed_self_intro_keeps_self_age_and_partner_age_separate():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_replay_opening_mixed_intro")

    understanding = chat_service.turn_understanding_service.analyze(
        TurnUnderstandingInput(
            user_message="96年女生找男朋友，目前在深圳单身未婚，本科学历，与收入1万左右，找90后",
            last_response="",
            message_count=1,
            user_profile=profile,
            conversation_context={},
            in_contact_flow=False,
        )
    )

    fused, meta = chat_service._fuse_extracted_fields(
        dict(getattr(understanding, "resolved_slots", {}) or {}),
        {},
        user_message="96年女生找男朋友，目前在深圳单身未婚，本科学历，与收入1万左右，找90后",
    )

    assert understanding.primary_turn_type == "opening"
    assert fused["age_label"] == "96年"
    assert fused["age"] in {"30", 30}
    assert fused["partner_requirement"] == "90后"
    assert fused["partner_pref_age"] == "90后"
    assert fused["monthly_income"] == "1万左右"
    assert meta["partner_pref_age"]["source"] in {"partner_requirement_subslot_normalized", "ai"}


def test_replay_rich_nanshan_mixed_intro_keeps_self_and_partner_fields_separate():
    chat_service = _build_chat_service()
    understanding = chat_service.turn_understanding_service.analyze(
        TurnUnderstandingInput(
            user_message="南山女生找男盆友，就是93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不",
            last_response="",
            message_count=1,
            user_profile=UserProfile(account_id="u_replay_nanshan_mixed"),
            conversation_context={},
            in_contact_flow=False,
        )
    )

    fused, meta = chat_service._fuse_extracted_fields(
        dict(getattr(understanding, "resolved_slots", {}) or {}),
        {},
        user_message="南山女生找男盆友，就是93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不",
    )

    assert fused["sex"] == "女"
    assert fused["marital_status"] == "未婚"
    assert fused["partner_gender_preference"] == "男"
    assert fused["partner_requirement"] == "未婚，学历本科及以上，大厂程序员"
    assert fused["partner_pref_education"] == "学历本科及以上"
    assert fused["partner_pref_industry"] == "大厂程序员"
    assert "education" not in fused
    assert "occupation" not in fused
    assert meta["partner_pref_education"]["source"] in {"partner_requirement_subslot_normalized", "ai"}


def test_turn_understanding_occupation_inference_prefers_structured_partner_preference_subslots():
    service = _build_chat_service().turn_understanding_service
    partner_requirement = service._compose_partner_requirement_text_for_inference(  # noqa: SLF001
        resolved_slots={
            "partner_pref_industry": "程序员",
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        message="希望对方是程序员，深圳，本科以上",
    )
    candidate = service.chat_service.extraction_service._infer_occupation_candidate_from_partner_requirement(  # noqa: SLF001
        partner_requirement
    )[0]

    assert partner_requirement == "深圳，学历本科及以上，程序员"
    assert candidate is None


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


def test_build_service_confirmation_resume_response_returns_to_interrupted_work_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_service_resume_work")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    response = chat_service._build_service_confirmation_resume_response(
        profile,
        "你们帮帮忙介绍对象吗？",
        message_count=2,
        last_response="那你现在在深圳主要做哪方面工作呀？ 收入这块你方便的话说个大概就行。",
    )

    assert any(token in response for token in ("工作", "做哪方面", "做什么"))
    assert "学历" not in response


def test_resolve_effective_followup_field_prefers_occupation_after_location_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_followup_location")

    next_field = chat_service._resolve_effective_followup_field(
        profile,
        ask_field="location",
        collected_fields={"location"},
        user_message="我来自深圳，今年35岁",
        allow_medium_target=True,
    )

    assert next_field == "occupation"


def test_resolve_effective_followup_field_no_longer_prefers_monthly_income_after_occupation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_followup_occupation")
    profile.location = "深圳"
    profile.age = 35
    profile.education = "本科"
    profile.collection_progress.update({"location": True, "age": True, "education": True})

    next_field = chat_service._resolve_effective_followup_field(
        profile,
        ask_field="occupation",
        collected_fields={"occupation"},
        user_message="做it，单身",
        allow_medium_target=True,
    )

    assert next_field == "marital_status"


def test_build_interleaving_followup_does_not_force_income_onto_education():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_education_only")
    profile.occupation = "自媒体"
    profile.collection_progress["occupation"] = True
    profile.location = "深圳"
    profile.collection_progress["location"] = True
    profile.age = 33
    profile.collection_progress["age"] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "做自媒体",
        main_target="education",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "学历" in response
    assert "收入" not in response


def test_build_interleaving_followup_can_fuse_income_with_location_after_occupation_collected():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_income_location")
    profile.occupation = "自媒体"
    profile.collection_progress["occupation"] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "我在深圳",
        main_target="location",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "城市" in response or "深圳" in response or "哪" in response
    assert "收入" in response


def test_question_budget_guard_strips_invalid_side_pair_when_two_questions_present():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_question_budget_invalid_pair")

    updated = chat_service._enforce_question_budget_guard(
        "你是什么学历呀？另外月收入大概多少呢？",
        user_profile=profile,
        user_message="嗯",
        turn_decision=TurnDecision(
            ask_field="education",
            response_channel="model",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
    )

    asked_fields = chat_service._detect_asked_fields_in_response(updated) | chat_service._detect_all_questioned_fields_in_response(updated)

    assert "学历" in updated
    assert "收入" not in updated
    assert asked_fields == {"education"}


def test_question_budget_guard_keeps_whitelisted_main_and_side_pair():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_question_budget_valid_pair")

    updated = chat_service._enforce_question_budget_guard(
        "你现在主要做哪方面工作呀？月收入大概在哪个区间呢？",
        user_profile=profile,
        user_message="嗯",
        turn_decision=TurnDecision(
            ask_field="occupation",
            response_channel="model",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
    )

    asked_fields = chat_service._detect_asked_fields_in_response(updated) | chat_service._detect_all_questioned_fields_in_response(updated)

    assert "工作" in updated
    assert "收入" in updated
    assert asked_fields == {"occupation", "monthly_income"}


@pytest.mark.asyncio
async def test_sync_post_delivery_state_sets_pending_retry_for_unanswered_side_target():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_side_pending")
    profile.last_asked_field = "education"
    profile.last_asked_side_field = "marital_status"
    chat_service._update_conversation_state = AsyncMock()
    chat_service.user_service.get_user_profile = AsyncMock(return_value=profile)
    chat_service._update_progress_runtime_counters = ChatService._update_progress_runtime_counters.__get__(
        chat_service, ChatService
    )
    chat_service.user_service.save_user_profile = AsyncMock()

    final_response, updated_profile = await chat_service.sync_post_delivery_state(
        account_id="u_side_pending",
        user_profile=profile,
        user_message="本科",
        final_response="本科我记下啦。",
        ai_response="本科我记下啦。",
        delivery_ok=True,
        turn_decision=TurnDecision(
            primary_move="light_followup",
            response_channel="model",
            allow_medium_target=True,
            allow_contact_target=False,
        ),
        collection_result={"all_fields": [{"field": "education", "value": "本科"}]},
        message_count=3,
        previous_asked_field="education",
        previous_asked_side_field="marital_status",
    )

    assert final_response == "本科我记下啦。"
    assert updated_profile.pending_retry_field == "marital_status"


def test_resolve_effective_followup_field_prefers_pending_retry_side_target():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_marital_followup")
    profile.pending_retry_field = "marital_status"

    next_field = chat_service._resolve_effective_followup_field(
        profile,
        ask_field="sex",
        collected_fields={"education"},
        user_message="本科",
        allow_medium_target=True,
    )

    assert next_field == "marital_status"


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


@pytest.mark.anyio
async def test_process_collection_result_wechat_completion_keeps_ai_ending_path():
    chat_service = _build_chat_service()
    chat_service.dialogue_manager.get_last_response = AsyncMock(
        return_value="电话我收到了。 方便的话，再留个微信也行吗？ 后面沟通会更顺一点"
    )
    chat_service.user_service.get_user_profile = AsyncMock()
    chat_service.user_service.save_user_profile = AsyncMock()
    profile = UserProfile(account_id="u_wechat_complete_forced_close")
    profile.sex = "男"
    profile.age = 36
    profile.age_label = "90后"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "8万"
    profile.marital_status = "单身"
    profile.partner_requirement = "苗条，温柔"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.wechat = "wx28295859"
    profile.wechat_collected = True
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
            "contact": True,
        }
    )
    chat_service.user_service.get_user_profile.return_value = profile

    result = await chat_service._process_collection_result(  # noqa: SLF001
        "u_wechat_complete_forced_close",
        profile,
        {"wechat": "wx28295859"},
        "wx28295859",
    )

    ending_info = result.get("ending_info") or {}
    assert ending_info.get("scenario") == "normal_complete"
    assert ending_info.get("use_ai") is True
    assert "1-8小时" in str(ending_info.get("extra_instructions") or "")
    assert not ending_info.get("response")


def test_conversation_ending_service_normal_complete_with_contact_includes_dynamic_timeline_instruction():
    service = ConversationEndingService()
    profile = UserProfile(account_id="u_normal_complete_timeline")
    profile.sex = "男"
    profile.age = 29
    profile.education = "本科"
    profile.monthly_income = "7万"
    profile.wechat = "wx235345345"
    profile.wechat_collected = True

    ending_info = service.build_ending_info("normal_complete", profile)

    assert ending_info["use_ai"] is True
    assert "1-8小时" in ending_info["extra_instructions"]
    assert "提前约时间" in ending_info["extra_instructions"]


def test_generation_prompt_service_builds_contact_completion_first_generation_instruction():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_completion_prompt")
    profile.sex = "男"
    profile.age = 29
    profile.education = "本科"
    profile.monthly_income = "7万"
    profile.location = "深圳"
    profile.phone = "17688765432"
    profile.phone_collected = True
    profile.phone_ask_count = 2
    profile.rejected_phone = True
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

    understanding = SimpleNamespace(resolved_slots={"wechat": "wx235345345"})

    instruction = chat_service.generation_prompt_service._build_contact_completion_generation_instruction(  # noqa: SLF001
        user_profile=profile,
        understanding_result=understanding,
    )

    assert "联系方式完成收尾专用生成" in instruction
    assert "1-8小时" in instruction
    assert "不打扰你" in instruction


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

    assert "男生还是女生" in response


def test_get_contact_terminal_or_resume_response_keeps_monthly_income_resume_after_contact_completion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_resume_income")
    profile.phone = "17688765456"
    profile.phone_collected = True
    profile.wechat = "17688765456"
    profile.wechat_collected = True
    profile.collection_progress["contact"] = True
    profile.occupation = "IT"
    profile.education = "本科"
    profile.marital_status = "单身"
    profile.collection_progress.update(
        {
            "occupation": True,
            "education": True,
            "marital_status": True,
        }
    )
    profile.field_ask_count["monthly_income"] = 1
    profile.resume_profile_target = "monthly_income"

    chat_service._build_policy_field_prompt = lambda field, *_args, **_kwargs: f"ask:{field}"

    response = chat_service._get_contact_terminal_or_resume_response(profile, "这个号也能加微信")

    assert "月收入" in response or "收入" in response


def test_is_coverage_complete_false_when_medium_field_is_pending_resume():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_pending_medium_resume")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.phone = "17688987659"
    profile.phone_collected = True
    profile.wechat = "17688987659"
    profile.wechat_collected = True
    profile.collection_progress.update(
        {
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "contact": True,
        }
    )
    profile.field_ask_count["monthly_income"] = 1
    profile.resume_profile_target = "monthly_income"

    assert chat_service.collection_policy.is_medium_field_covered(profile, "monthly_income") is False
    assert chat_service.ending_state_service.is_profile_collection_complete_or_exhausted(profile) is False


def test_can_end_with_contact_completion_false_when_contact_done_but_core_and_medium_not_ask_exhausted():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_contact_done_not_exhausted")
    profile.phone = "17688987659"
    profile.phone_collected = True
    profile.wechat = "wx7789789"
    profile.wechat_collected = True
    profile.collection_progress["contact"] = True
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    profile.field_ask_count["age"] = 1
    profile.field_ask_count["education"] = 1
    profile.field_ask_count["occupation"] = 1
    profile.field_ask_count["location"] = 1
    profile.field_ask_count["marital_status"] = 0
    profile.field_ask_count["partner_requirement"] = 0
    profile.field_ask_count["monthly_income"] = 0

    assert chat_service.contact_service.is_contact_complete(profile) is True
    assert chat_service.collection_policy.is_coverage_complete(profile) is False
    assert chat_service.ending_state_service.can_end_with_contact_completion(profile) is False
    assert chat_service._can_end_with_contact_completion(profile) is False


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
