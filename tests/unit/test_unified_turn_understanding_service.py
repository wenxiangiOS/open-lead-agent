from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.conversation_understanding.domain.semantic_understanding_layer import SemanticUnderstandingLayer
from src.modules.conversation_understanding.domain.unified_turn_understanding_service import (
    UnifiedTurnUnderstandingService,
)


class _StubChatService:
    def __init__(self):
        self.user_question_service = SimpleNamespace(
            detect_quick_faq_intent=lambda message: None
        )
        self.expectation_service = SimpleNamespace(
            is_matching_timeline_question=lambda message: False
        )


def _make_input(
    message: str,
    *,
    last_response: str = "",
    in_contact_flow: bool = False,
    user_profile=None,
    pending_confirmation_field=None,
):
    return TurnUnderstandingInput(
        user_message=message,
        last_response=last_response,
        message_count=3,
        user_profile=user_profile or SimpleNamespace(),
        conversation_context={"recent_responses": [last_response] if last_response else []},
        in_contact_flow=in_contact_flow,
        pending_confirmation_field=pending_confirmation_field,
    )


class _DelegatingSemanticService:
    def __init__(self, result: TurnUnderstandingResult):
        self._base = TurnUnderstandingService(_StubChatService())
        self._result = result

    def analyze(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:  # noqa: ARG002
        return TurnUnderstandingResult(
            primary_turn_type=self._result.primary_turn_type,
            subtype=self._result.subtype,
            complaint_reason=self._result.complaint_reason,
            resume_profile_collection=self._result.resume_profile_collection,
            post_answer_reentry=self._result.post_answer_reentry,
            secondary_signals=list(self._result.secondary_signals or []),
            risk_flags=list(self._result.risk_flags or []),
            slot_candidates=dict(self._result.slot_candidates or {}),
            resolved_slots=dict(self._result.resolved_slots or {}),
            blocked_slots=dict(self._result.blocked_slots or {}),
            answer_first=self._result.answer_first,
            resume_hint=self._result.resume_hint,
            context_ack_type=self._result.context_ack_type,
            context_ack_payload=dict(self._result.context_ack_payload or {}),
            context_ack_occupation=self._result.context_ack_occupation,
            context_ack_location=self._result.context_ack_location,
            context_ack_preference=self._result.context_ack_preference,
            context_ack_field_ack=self._result.context_ack_field_ack,
            soft_retry_field=self._result.soft_retry_field,
            pre_generation_resolution=self._result.pre_generation_resolution,
            confidence=self._result.confidence,
            notes=list(self._result.notes or []),
        )

    def __getattr__(self, item):
        return getattr(self._base, item)


def test_semantic_understanding_layer_prefers_raw_semantic_path_when_available():
    called = {"raw": False, "normal": False}

    class _SemanticService:
        def analyze(self, turn_input):  # noqa: ARG002
            called["normal"] = True
            return TurnUnderstandingResult(primary_turn_type="opening", subtype="greeting", confidence=0.8)

        def analyze_without_slot_governance(self, turn_input):  # noqa: ARG002
            called["raw"] = True
            return TurnUnderstandingResult(primary_turn_type="opening", subtype="greeting", confidence=0.8)

    layer = SemanticUnderstandingLayer(_SemanticService())
    result = layer.analyze(_make_input("你好"))

    assert result.primary_turn_type == "opening"
    assert called["raw"] is True
    assert called["normal"] is False


def test_unified_understanding_governance_suppresses_age_in_contact_flow():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_context_reply",
            resolved_slots={"age": "18"},
            confidence=0.93,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "1879987654",
                last_response="方便留个电话吗？",
                in_contact_flow=True,
            )
        )
    )

    assert "age" not in result.resolved_slots
    assert result.blocked_slots["age"].reason == "contact_context_prefers_contact_over_age"


def test_unified_understanding_governance_prioritizes_explicit_correction():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="correction",
            subtype="active_revise",
            resolved_slots={"education": "本科"},
            confidence=0.95,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "不是本科，是大专",
                last_response="你方便留个电话吗？",
                in_contact_flow=True,
                user_profile=SimpleNamespace(education="本科"),
            )
        )
    )

    assert result.resolved_slots["education"] == "大专"
