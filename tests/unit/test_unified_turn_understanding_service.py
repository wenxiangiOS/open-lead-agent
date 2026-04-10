from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.modules.conversation.domain.turn_understanding_models import SlotCandidate, TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.conversation_understanding.domain.semantic_understanding_layer import SemanticUnderstandingLayer
from src.modules.conversation_understanding.domain.unified_turn_understanding_service import (
    UnifiedTurnUnderstandingService,
)


class _StubChatService:
    def __init__(self):
        self.extraction_service = ExtractionService(SimpleNamespace())
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
        slot_candidates = dict(self._result.slot_candidates or {})
        if not slot_candidates:
            slot_candidates = {
                field: SlotCandidate(
                    value=str(value),
                    confidence=self._result.confidence or 0.9,
                    source="test_stub",
                    source_text=str(turn_input.user_message or ""),
                )
                for field, value in dict(self._result.resolved_slots or {}).items()
            }
        return TurnUnderstandingResult(
            primary_turn_type=self._result.primary_turn_type,
            subtype=self._result.subtype,
            complaint_reason=self._result.complaint_reason,
            resume_profile_collection=self._result.resume_profile_collection,
            post_answer_reentry=self._result.post_answer_reentry,
            secondary_signals=list(self._result.secondary_signals or []),
            risk_flags=list(self._result.risk_flags or []),
            slot_candidates=slot_candidates,
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

    def analyze_without_slot_governance(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:  # noqa: ARG002
        return self.analyze(turn_input)

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
    if "age" in result.blocked_slots:
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


def test_unified_understanding_governance_blocks_age_pollution_in_income_message():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
            resolved_slots={"age": "20", "monthly_income": "20万"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "我月薪20万",
                last_response="你现在月收入大概在哪个区间呀？",
            )
        )
    )

    assert "age" not in result.resolved_slots
    assert result.resolved_slots["monthly_income"] == "20万"


def test_unified_understanding_faq_turn_blocks_profile_slot_writeback():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="faq_concern",
            subtype="opening_clarify",
            resolved_slots={"occupation": "可以", "location": "香港"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "可以啊 机构是吗 资源怎么样啊",
                last_response="你好呀，方便简单了解下吗？",
            )
        )
    )

    assert result.resolved_slots == {}


def test_unified_understanding_question_state_prioritizes_asked_income_field():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"age": "20", "monthly_income": "20k+", "location": "香港"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["monthly_income"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "月搜入大概20k+",
                last_response="你现在月收入大概在哪个区间呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots == {"monthly_income": "20k+"}


def test_unified_understanding_question_state_allows_side_field_in_mixed_answer():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"monthly_income": "20k+", "occupation": "产品", "age": "20"},
            confidence=0.91,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["monthly_income"],
            "side_fields": ["occupation"],
            "expected_scope": "self",
            "allow_mixed_answer": True,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "20k+，做产品",
                last_response="你现在是做什么工作的呀，大概收入在什么范围呢？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots["monthly_income"] == "20k+"
    assert result.resolved_slots["occupation"] == "产品"
    assert "age" not in result.resolved_slots


def test_unified_understanding_question_state_keeps_correction_even_when_field_not_asked():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="correction",
            subtype="active_revise",
            resolved_slots={"education": "本科"},
            confidence=0.95,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        education="本科",
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["monthly_income"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        },
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "不是本科，是大专",
                last_response="你现在月收入大概在哪个区间呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots["education"] == "大专"


def test_unified_understanding_question_state_prioritizes_occupation_field():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"occupation": "产品", "age": "20", "partner_requirement": "香港"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["occupation"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "做产品",
                last_response="你现在是做什么工作的呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots == {"occupation": "产品"}


def test_unified_understanding_question_state_prioritizes_education_field():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"education": "本科", "age": "20", "partner_requirement": "本科及以上"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["education"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "本科",
                last_response="你是什么学历呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots == {"education": "本科"}


def test_unified_understanding_question_state_prioritizes_marital_status_field():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"marital_status": "未婚", "age": "20", "partner_requirement": "未婚"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["marital_status"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "未婚",
                last_response="你现在感情状态怎么样呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots == {"marital_status": "未婚"}


def test_unified_understanding_question_signal_without_asked_fields_preserves_mixed_payload():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"sex": "女", "partner_requirement": "香港"},
            confidence=0.85,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "女生 香港有不",
                last_response="你是男生还是女生呀？",
            )
        )
    )

    assert result.resolved_slots["sex"] == "女"


def test_unified_understanding_rebuilds_resolved_slots_from_filtered_candidates():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            slot_candidates={},
            resolved_slots={"occupation": "产品", "age": "20"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["occupation"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    # Simulate the common path where slot_candidates are present but resolved_slots are stale.
    semantic_service._result.slot_candidates = {
        "occupation": SimpleNamespace(value="产品", confidence=0.9, source="rule", source_text="做产品"),
        "age": SimpleNamespace(value="20", confidence=0.9, source="rule", source_text="做产品"),
    }

    result = asyncio.run(
        service.analyze(
            _make_input(
                "做产品",
                last_response="你现在是做什么工作的呀？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots == {"occupation": "产品"}


def test_unified_understanding_builds_resolved_field_evidence_and_age_derivation():
    base = TurnUnderstandingService(_StubChatService())
    semantic_result = base.analyze(_make_input("95想找90后都可以有不"))
    service = UnifiedTurnUnderstandingService(_DelegatingSemanticService(semantic_result), ai_service=None)

    result = asyncio.run(service.analyze(_make_input("95想找90后都可以有不")))

    assert result.resolved_slots["age_label"] == "95年"
    assert result.field_derivations["age_label"] == "95年"
    assert result.resolved_field_evidence["age"].scope == "self"
    assert result.resolved_field_evidence["age_label"].scope == "self"
    assert result.resolved_field_evidence["partner_requirement"].scope == "partner"
