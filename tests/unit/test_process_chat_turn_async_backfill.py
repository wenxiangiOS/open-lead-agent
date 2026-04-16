from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase
from src.modules.conversation.domain.turn_understanding_models import TurnPriorityDecision
from src.modules.conversation_understanding.domain.async_semantic_backfill_policy_service import (
    AsyncSemanticBackfillPolicyService,
)
from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    FieldObservation,
    PendingField,
    TurnPersistencePlan,
    TurnSemanticFrame,
    UserQuestion,
)


class _RuntimeStubChatService:
    def __init__(self):
        self.unified_turn_understanding_service = object()
        self.collection_extraction_service = object()


def _make_schedulable_turn_understanding():
    semantic_frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="mixed",
        user_questions=[UserQuestion(topic="pricing", question_text="怎么收费", confidence=0.98)],
        field_observations=[
            FieldObservation(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                owner="self",
                evidence_text="深圳龙华在编女教师",
                evidence_span="在编女教师",
                confidence=0.91,
                write_mode="direct_write",
                source="semantic_deterministic",
            ),
            FieldObservation(
                field="partner_requirement",
                value="同老家在深圳，最好深户，有房有车",
                normalized_value="同老家在深圳，最好深户，有房有车",
                scope="partner",
                owner="partner",
                evidence_text="找同老家在深圳 最好深户 有房有车",
                evidence_span="同老家在深圳 最好深户 有房有车",
                confidence=0.86,
                write_mode="direct_write",
                source="semantic_deterministic",
            ),
            FieldObservation(
                field="phone",
                value="13526783627",
                normalized_value="13526783627",
                scope="contact",
                owner="self",
                evidence_text="可以直接电话联系这边13526783627",
                evidence_span="13526783627",
                confidence=0.99,
                write_mode="direct_write",
                source="semantic_deterministic",
            ),
        ],
        confidence=0.93,
    )
    persistence_plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="location",
                value="深圳龙华",
                normalized_value="深圳龙华",
                scope="self",
                evidence_text="深圳龙华",
                confidence=0.96,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
            )
        ],
        provisional_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="在编女教师",
                confidence=0.91,
                acceptance_reason="high_risk_non_ai_guard",
                update_action="stage_as_provisional",
                persistence_state="provisional",
                risk_level="high",
                source_channel="fallback",
            ),
            AcceptedField(
                field="partner_requirement",
                value="同老家在深圳，最好深户，有房有车",
                normalized_value="同老家在深圳，最好深户，有房有车",
                scope="partner",
                evidence_text="找同老家在深圳 最好深户 有房有车",
                confidence=0.86,
                acceptance_reason="high_risk_non_ai_guard",
                update_action="stage_as_provisional",
                persistence_state="provisional",
                risk_level="high",
                source_channel="fallback",
            ),
        ],
        pending_fields=[
            PendingField(
                field="phone",
                candidate_value="13526783627",
                reason="low_confidence_high_risk",
                scope="contact",
                persistence_state="pending_confirm",
                risk_level="high",
                source_channel="fallback",
            )
        ],
    )
    return SimpleNamespace(
        persistence_plan=persistence_plan,
        semantic_frame=semantic_frame,
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        priority_decision=TurnPriorityDecision(
            primary_task="user_question",
            priority_level=2,
            decision_reason="faq:fee",
            response_mode="answer_then_resume",
            prioritize_user_question=True,
        ),
        resolved_slots={
            "location": "深圳龙华",
            "occupation": "在编教师",
            "partner_requirement": "同老家在深圳，最好深户，有房有车",
            "phone": "13526783627",
        },
    )


def _make_pure_faq_turn_understanding():
    semantic_frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="faq",
        user_questions=[UserQuestion(topic="pricing", question_text="怎么收费", confidence=0.98)],
        field_observations=[],
        confidence=0.9,
    )
    return SimpleNamespace(
        persistence_plan=TurnPersistencePlan(),
        semantic_frame=semantic_frame,
        primary_turn_type="faq_concern",
        subtype="fee",
        priority_decision=TurnPriorityDecision(
            primary_task="user_question",
            priority_level=2,
            decision_reason="faq:fee",
            response_mode="answer_only",
            prioritize_user_question=True,
        ),
        resolved_slots={},
    )


def test_async_backfill_policy_schedules_high_value_mixed_turn():
    service = AsyncSemanticBackfillPolicyService()

    decision = service.decide(
        route_name="quick_faq",
        user_message="深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费",
        turn_understanding=_make_schedulable_turn_understanding(),
    )

    assert decision.should_schedule is True
    assert "pending_or_provisional" in decision.reason
    assert "high_risk" in decision.reason
    assert "mixed_question" in decision.reason
    assert decision.target_fields == ["phone", "occupation", "partner_requirement"]
    assert decision.fingerprint


def test_async_backfill_policy_skips_pure_faq_without_new_fields():
    service = AsyncSemanticBackfillPolicyService()

    decision = service.decide(
        route_name="quick_faq",
        user_message="怎么收费",
        turn_understanding=_make_pure_faq_turn_understanding(),
    )

    assert decision.should_schedule is False
    assert decision.reason == "pure_user_question"


def test_async_backfill_policy_ai_success_with_gaps_still_schedules():
    service = AsyncSemanticBackfillPolicyService()
    turn_understanding = _make_schedulable_turn_understanding()
    turn_understanding.semantic_frame.source = "ai_structured_extraction"

    decision = service.decide(
        route_name="model",
        user_message="深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费",
        turn_understanding=turn_understanding,
    )

    assert decision.should_schedule is True
    assert "pending_or_provisional" in decision.reason


def test_async_backfill_policy_ai_success_without_gaps_skips():
    service = AsyncSemanticBackfillPolicyService()
    semantic_frame = TurnSemanticFrame(
        version="v1",
        source="ai_structured_extraction",
        primary_domain="mixed",
        notes=[
            "partner_summary=90后男生，工作稳定",
            "soft_profile_summary=喜欢旅游，感情经历简单",
        ],
        field_observations=[
            FieldObservation(
                field="sex",
                value="女",
                normalized_value="女",
                scope="self",
                owner="self",
                evidence_text="女生",
                evidence_span="女生",
                confidence=0.97,
                write_mode="direct_write",
                source="ai_semantic_extraction",
            ),
            FieldObservation(
                field="location",
                value="深圳南山",
                normalized_value="深圳南山",
                scope="self",
                owner="self",
                evidence_text="深圳南山",
                evidence_span="深圳南山",
                confidence=0.97,
                write_mode="direct_write",
                source="ai_semantic_extraction",
            ),
        ],
        confidence=0.95,
    )
    turn_understanding = SimpleNamespace(
        persistence_plan=TurnPersistencePlan(),
        semantic_frame=semantic_frame,
        primary_turn_type="opening",
        subtype="dense_intro",
        priority_decision=TurnPriorityDecision(
            primary_task="core_profile_collection",
            priority_level=5,
            decision_reason="core_profile_signal_detected",
            response_mode="ask_only",
        ),
        resolved_slots={"sex": "女", "location": "深圳南山"},
    )

    decision = service.decide(
        route_name="model",
        user_message="98年女生，深圳南山，本科学历，喜欢旅游，找90后男生，工作稳定就行",
        turn_understanding=turn_understanding,
    )

    assert decision.should_schedule is False
    assert decision.reason == "already_ai"


@pytest.mark.asyncio
async def test_schedule_async_backfill_skips_duplicate_fingerprint(monkeypatch):
    monkeypatch.setenv("UNIFIED_TURN_ASYNC_BACKFILL_ENABLED", "1")
    use_case = ProcessChatTurnUseCase(chat_service=_RuntimeStubChatService())
    turn_understanding = _make_schedulable_turn_understanding()

    async def _fake_run_async_semantic_backfill(**kwargs):
        return {
            "account_id": kwargs["account_id"],
            "applied": 2,
            "reason": "ok",
            "outcome": "success",
            "latency_ms": 1,
        }

    use_case._run_async_semantic_backfill = _fake_run_async_semantic_backfill

    use_case._schedule_async_semantic_backfill(
        route_name="quick_faq",
        account_id="u_async_backfill",
        user_message="深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费",
        dialog_id="dlg_async_backfill",
        message_count=5,
        conversation_context={},
        turn_understanding=turn_understanding,
    )
    await asyncio.sleep(0.01)

    use_case._schedule_async_semantic_backfill(
        route_name="quick_faq",
        account_id="u_async_backfill",
        user_message="深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费",
        dialog_id="dlg_async_backfill",
        message_count=5,
        conversation_context={},
        turn_understanding=turn_understanding,
    )

    assert use_case._async_backfill_obs["scheduled"] == 1
    assert use_case._async_backfill_obs["skip"] >= 1


def test_schedule_async_backfill_respects_cooldown(monkeypatch):
    monkeypatch.setenv("UNIFIED_TURN_ASYNC_BACKFILL_ENABLED", "1")
    use_case = ProcessChatTurnUseCase(chat_service=_RuntimeStubChatService())
    use_case._async_backfill_cooldown_until_by_account["u_async_backfill"] = time.monotonic() + 30

    use_case._schedule_async_semantic_backfill(
        route_name="quick_faq",
        account_id="u_async_backfill",
        user_message="深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费",
        dialog_id="dlg_async_backfill",
        message_count=5,
        conversation_context={},
        turn_understanding=_make_schedulable_turn_understanding(),
    )

    assert use_case._async_backfill_obs["scheduled"] == 0
    assert use_case._async_backfill_obs["skip"] == 1
