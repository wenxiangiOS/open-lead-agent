from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import (
    TurnPriorityDecision,
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    TurnPersistencePlan,
)
from src.modules.conversation_understanding.domain.turn_priority_policy import TurnPriorityPolicy
from src.services.core.chat_service import ChatService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):  # noqa: ARG002
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), AsyncMock())


def _make_turn_input(
    message: str,
    *,
    profile=None,
    last_response: str = "",
    in_contact_flow: bool = False,
) -> TurnUnderstandingInput:
    return TurnUnderstandingInput(
        user_message=message,
        last_response=last_response,
        message_count=4,
        user_profile=profile or UserProfile(account_id="u_priority_default"),
        conversation_context={"recent_responses": [last_response] if last_response else []},
        in_contact_flow=in_contact_flow,
    )


def _accepted_field(field: str, value: str, *, scope: str = "self") -> AcceptedField:
    return AcceptedField(
        field=field,
        value=value,
        normalized_value=value,
        scope=scope,
        evidence_text=str(value),
        confidence=0.96,
        acceptance_reason="direct_write",
        update_action="accept_as_new",
    )


def test_turn_priority_policy_prefers_user_question_over_contact_and_preference_signals():
    policy = TurnPriorityPolicy()
    profile = UserProfile(account_id="u_priority_faq")
    turn_input = _make_turn_input(
        "深圳龙华在编教师，可以直接电话联系13526783627，怎么收费呢先了解下",
        profile=profile,
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="fee",
        resolved_slots={"occupation": "在编教师", "phone": "13526783627", "partner_requirement": "同老家在深圳"},
        confidence=0.93,
    )
    plan = TurnPersistencePlan(
        accepted_fields=[
            _accepted_field("occupation", "在编教师"),
            _accepted_field("phone", "13526783627", scope="contact"),
            _accepted_field("partner_requirement", "同老家在深圳", scope="partner"),
        ]
    )

    decision = policy.decide(
        turn_input=turn_input,
        semantic_result=semantic_result,
        persistence_plan=plan,
    )

    assert decision.primary_task == "user_question"
    assert decision.priority_level == 2
    assert decision.response_mode == "answer_then_resume"
    assert "contact_record" in decision.suppressed_tasks
    assert "core_profile_collection" in decision.suppressed_tasks
    assert "preference_collection" in decision.suppressed_tasks


def test_turn_priority_policy_prefers_status_confirmation_over_contact_and_core_when_divorce_pending():
    policy = TurnPriorityPolicy()
    profile = UserProfile(account_id="u_priority_divorce")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    turn_input = _make_turn_input(
        "我在深圳做老师",
        profile=profile,
        last_response="离异这个我记下了，那手续现在都办妥了吗？",
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"location": "深圳", "occupation": "老师"},
        confidence=0.9,
    )
    plan = TurnPersistencePlan(
        accepted_fields=[
            _accepted_field("location", "深圳"),
            _accepted_field("occupation", "老师"),
        ]
    )

    decision = policy.decide(
        turn_input=turn_input,
        semantic_result=semantic_result,
        persistence_plan=plan,
    )

    assert decision.primary_task == "status_confirmation"
    assert decision.locked_field == "marital_status"
    assert decision.decision_reason == "divorce_confirmation_pending"
    assert "core_profile_collection" in decision.suppressed_tasks


def test_turn_priority_policy_skips_birth_year_status_lock_when_user_gives_specific_year_with_compound_message():
    policy = TurnPriorityPolicy()
    profile = UserProfile(account_id="u_priority_birth_year_compound")
    profile.pending_birth_year_bucket = "90后"
    profile.birth_year_confirmation_closed = False
    turn_input = _make_turn_input(
        "98年的，喜欢成熟稳重，多金，身高180+",
        profile=profile,
        last_response="你具体是哪一年出生的呀？另外择偶方面你更看重哪一点呢？",
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"partner_requirement": "成熟稳重，多金，身高180+"},
        confidence=0.9,
    )
    plan = TurnPersistencePlan(
        accepted_fields=[
            _accepted_field("partner_requirement", "成熟稳重，多金，身高180+", scope="partner"),
        ]
    )

    decision = policy.decide(
        turn_input=turn_input,
        semantic_result=semantic_result,
        persistence_plan=plan,
    )

    assert decision.primary_task != "status_confirmation"
    assert decision.locked_field is None


def test_turn_priority_policy_prefers_core_collection_over_contact_record_for_mixed_intro():
    policy = TurnPriorityPolicy()
    profile = UserProfile(account_id="u_priority_contact")
    turn_input = _make_turn_input(
        "我在深圳做老师，找本科男生，可以直接联系13526783627",
        profile=profile,
        in_contact_flow=True,
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"phone": "13526783627", "occupation": "老师", "partner_requirement": "本科男生"},
        confidence=0.94,
    )
    plan = TurnPersistencePlan(
        accepted_fields=[
            _accepted_field("phone", "13526783627", scope="contact"),
            _accepted_field("occupation", "老师"),
            _accepted_field("partner_requirement", "本科男生", scope="partner"),
        ]
    )

    decision = policy.decide(
        turn_input=turn_input,
        semantic_result=semantic_result,
        persistence_plan=plan,
    )

    assert decision.primary_task == "core_profile_collection"
    assert decision.priority_level == 5
    assert decision.defer_complementary_contact is False
    assert "contact_record" not in decision.suppressed_tasks
    assert "preference_collection" in decision.suppressed_tasks


def test_turn_priority_policy_keeps_contact_record_for_pure_contact_turn():
    policy = TurnPriorityPolicy()
    profile = UserProfile(account_id="u_priority_contact_only")
    turn_input = _make_turn_input(
        "微信就是abc123456",
        profile=profile,
        in_contact_flow=True,
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        resolved_slots={"wechat": "abc123456"},
        confidence=0.94,
    )
    plan = TurnPersistencePlan(
        accepted_fields=[_accepted_field("wechat", "abc123456", scope="contact")]
    )

    decision = policy.decide(
        turn_input=turn_input,
        semantic_result=semantic_result,
        persistence_plan=plan,
    )

    assert decision.primary_task == "contact_record"
    assert decision.priority_level == 4
    assert decision.defer_complementary_contact is True


@pytest.mark.asyncio
async def test_build_turn_decision_async_uses_status_priority_lock():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_priority_decision_status")
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        confidence=0.9,
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

    decision = await chat_service._build_turn_decision_async(
        user_message="我在深圳工作",
        user_profile=profile,
        conversation_context={"message_count": 4, "recent_responses": ["离异这个我记下了，那手续都办妥了吗？"]},
        understanding_result=understanding,
    )

    assert decision.primary_move == "confirm_status_only"
    assert decision.ask_field == "marital_status"
    assert decision.priority_primary_task == "status_confirmation"
    assert decision.priority_reason == "divorce_confirmation_pending"


@pytest.mark.asyncio
async def test_build_turn_decision_async_respects_user_question_priority_from_policy():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_priority_decision_faq")
    understanding = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        confidence=0.9,
        priority_decision=TurnPriorityDecision(
            primary_task="user_question",
            priority_level=2,
            decision_reason="faq:fee",
            response_mode="answer_then_resume",
            prioritized_question_intent="fee",
            allow_contact_target=False,
            allow_medium_target=False,
            prioritize_user_question=True,
            suppressed_tasks=["contact_record", "core_profile_collection"],
        ),
    )

    decision = await chat_service._build_turn_decision_async(
        user_message="13526783627，怎么收费呢",
        user_profile=profile,
        conversation_context={"message_count": 4, "recent_responses": ["方便留个电话吗？"]},
        understanding_result=understanding,
    )

    assert decision.prioritize_user_question is True
    assert decision.response_channel == "quick_faq"
    assert decision.allow_contact_target is False
    assert decision.priority_primary_task == "user_question"
    assert decision.priority_reason == "faq:fee"
