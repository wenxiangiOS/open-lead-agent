from __future__ import annotations

import asyncio
import logging
import os
from types import SimpleNamespace

from src.core.exceptions import AIServiceException
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.conversation_understanding.domain.ai_semantic_extraction_service import AISemanticExtractionService
from src.modules.conversation_understanding.domain.contextual_slot_governance_layer import ContextualSlotGovernanceLayer
from src.modules.conversation_understanding.domain.field_derivation_layer import FieldDerivationLayer
from src.modules.conversation_understanding.domain.field_permission_layer import FieldPermissionLayer
from src.modules.conversation_understanding.domain.field_update_policy_service import FieldUpdatePolicyService
from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    ReplyActClassificationResult,
    TurnInputSnapshot,
    TurnSemanticFrame,
    TurnPersistencePlan,
)
from src.modules.conversation_understanding.domain.reply_act_classification_layer import ReplyActClassificationLayer
from src.modules.profile_collection.domain.extraction_service import ExtractionService


def _make_input(message: str, *, last_response: str = "") -> TurnUnderstandingInput:
    return TurnUnderstandingInput(
        user_message=message,
        last_response=last_response,
        message_count=1,
        user_profile=SimpleNamespace(),
        conversation_context={},
        in_contact_flow=False,
    )


def test_reply_act_classification_reads_persistence_plan_payload_when_legacy_slots_empty():
    layer = ReplyActClassificationLayer()
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="general_faq",
        resolved_slots={},
        confidence=0.88,
    )
    setattr(
        semantic_result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="在编教师",
                    normalized_value="在编教师",
                    scope="self",
                    evidence_text="深圳龙华在编女教师",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    result = layer.classify(
        turn_input=_make_input("对啦怎么收费呢先了解下"),
        semantic_result=semantic_result,
        question_state=None,
    )

    assert result.reply_act == "mixed_answer"
    assert result.reason == "question_signal_with_payload"


def test_field_permission_filter_result_keeps_persistence_plan_fields_when_allowed():
    layer = FieldPermissionLayer()
    result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        resolved_slots={},
        slot_candidates={},
        confidence=0.9,
    )
    setattr(
        result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="产品",
                    normalized_value="产品",
                    scope="self",
                    evidence_text="做产品",
                    confidence=0.9,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    filtered = layer.filter_result(
        result=result,
        permission_result=SimpleNamespace(
            allowed_fields={"occupation"},
            blocked_fields=set(),
        ),
    )

    assert filtered.resolved_slots == {"occupation": "产品"}


def test_field_permission_decide_does_not_shrink_mixed_payload_to_legacy_resolved_fields():
    layer = FieldPermissionLayer()
    result = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        resolved_slots={"phone": "13526783627"},
        confidence=0.93,
    )

    permission = layer.decide(
        turn_input=_make_input(
            "深圳龙华在编女教师，河南人165/104，可以直接电话联系这边13526783627，对啦怎么收费呢先了解下"
        ),
        semantic_result=result,
        reply_act_result=ReplyActClassificationResult(reply_act="contact_answer", confidence=0.9, reason="test"),
        question_state={},
    )

    assert permission.allowed_fields == set()
    assert permission.blocked_fields == set()
    assert permission.allowed_scope == "mixed"
    assert permission.allow_mixed_answer is True


def test_contextual_governance_backfill_syncs_persistence_plan_for_sex_confirmation():
    layer = ContextualSlotGovernanceLayer(
        SimpleNamespace(
            _extract_confirmed_sex_candidate_from_context=lambda last_response: "女" if "女生" in str(last_response or "") else None,
            _extract_deterministic_profile_fields=lambda message: {},
            _looks_like_correction=lambda message: False,
            chat_service=None,
        )
    )
    result = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="ambiguous_short_answer",
        resolved_slots={},
        slot_candidates={},
        confidence=0.8,
    )
    setattr(result, "persistence_plan", TurnPersistencePlan())

    governed = layer.govern(
        turn_input=_make_input("是女生", last_response="你是女生对吧？"),
        result=result,
    )

    assert governed.resolved_slots["sex"] == "女"
    assert any(
        str(getattr(item, "field", "") or "") == "sex"
        and str(getattr(item, "normalized_value", "") or "") == "女"
        for item in list(getattr(governed.persistence_plan, "accepted_fields", []) or [])
    )


def test_contextual_governance_block_field_removes_persistence_plan_entry():
    layer = ContextualSlotGovernanceLayer(SimpleNamespace())
    result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        resolved_slots={},
        slot_candidates={},
        confidence=0.8,
    )
    setattr(
        result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="occupation",
                    value="未婚",
                    normalized_value="未婚",
                    scope="self",
                    evidence_text="未婚",
                    confidence=0.9,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    layer._block_field(result, "occupation", "looks_like_marital_status_not_occupation", "未婚")  # noqa: SLF001

    assert "occupation" in result.blocked_slots
    assert not list(getattr(result.persistence_plan, "accepted_fields", []) or [])


def test_field_derivation_reads_partner_requirement_from_persistence_plan_and_syncs_derived_fields():
    layer = FieldDerivationLayer()
    result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        resolved_slots={},
        resolved_field_evidence={},
        field_derivations={},
        confidence=0.9,
    )
    setattr(
        result,
        "persistence_plan",
        TurnPersistencePlan(
            accepted_fields=[
                AcceptedField(
                    field="partner_requirement",
                    value="同医疗体系，同在深圳发展，本地优先，比自己大",
                    normalized_value="同医疗体系，同在深圳发展，本地优先，比自己大",
                    scope="partner",
                    evidence_text="同医疗体系，同在深圳发展，本地优先，比自己大",
                    confidence=0.95,
                    acceptance_reason="direct_write",
                    update_action="accept_as_new",
                )
            ]
        ),
    )

    derived = layer.derive(result=result)

    assert derived.resolved_slots["partner_pref_industry"] == "同医疗体系"
    assert derived.resolved_slots["partner_pref_location"] == "深圳"
    assert derived.resolved_slots["partner_pref_locality"] == "本地优先"
    assert derived.resolved_slots["partner_pref_age_relation"] == "比自己大"
    accepted_fields = list(getattr(derived.persistence_plan, "accepted_fields", []) or [])
    accepted_names = {str(getattr(item, "field", "") or "") for item in accepted_fields}
    assert "partner_pref_industry" in accepted_names
    assert "partner_pref_location" in accepted_names


def test_ai_semantic_extraction_keeps_age_followup_answer_even_without_profile_intro():
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {"age": "36", "age_label": "90后"},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=None)
    snapshot = TurnInputSnapshot(
        user_message="90后啊",
        last_response="你今年大概多大呀？",
        message_count=3,
        prompt_state={"asked_fields": ["age"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )

    observations = service._extract_direct_observations(snapshot)  # noqa: SLF001
    age_items = [item for item in observations if str(getattr(item, "field", "") or "") == "age"]

    assert age_items
    assert str(getattr(age_items[0], "source", "") or "") == "semantic_explicit_self_marker"


def test_ai_semantic_extraction_drops_age_when_not_followup_and_not_profile_intro():
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {"age": "36", "age_label": "90后"},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=None)
    snapshot = TurnInputSnapshot(
        user_message="90后啊",
        last_response="",
        message_count=1,
        prompt_state={"asked_fields": [], "side_fields": []},
        user_profile=SimpleNamespace(),
    )

    observations = service._extract_direct_observations(snapshot)  # noqa: SLF001
    age_fields = {
        str(getattr(item, "field", "") or "")
        for item in observations
    }
    assert "age" not in age_fields
    assert "age_label" not in age_fields


def test_ai_semantic_extraction_retries_after_first_failure_with_retry_budget():
    class _FlakyAIService:
        def __init__(self):
            self.calls = []

        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            self.calls.append(dict(kwargs or {}))
            if len(self.calls) == 1:
                raise AIServiceException("timeout")
            return (
                '{"primary_domain":"profile","acts":[],"user_questions":[],"field_observations":['
                '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self",'
                '"evidence_text":"在编教师","evidence_span":"在编教师","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
                '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
            )

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    ai_service = _FlakyAIService()
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=ai_service)
    snapshot = TurnInputSnapshot(
        user_message="在编教师",
        last_response="你现在是做哪方面工作的呀？",
        message_count=3,
        prompt_state={"asked_fields": ["occupation"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="profile_answer", subtype="single_slot_answer", confidence=0.9)

    timeout_key = "UNIFIED_TURN_SYNC_AI_RETRY_TIMEOUT_SECONDS"
    model_key = "UNIFIED_TURN_SYNC_AI_RETRY_MODEL"
    retry_enabled_key = "UNIFIED_TURN_SYNC_AI_RETRY_ENABLED"
    old_timeout = os.environ.get(timeout_key)
    old_model = os.environ.get(model_key)
    old_retry_enabled = os.environ.get(retry_enabled_key)
    os.environ[timeout_key] = "7"
    os.environ[model_key] = "fallback-test-model"
    os.environ[retry_enabled_key] = "1"
    try:
        frame = asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=11.0,
            )
        )
    finally:
        if old_timeout is None:
            os.environ.pop(timeout_key, None)
        else:
            os.environ[timeout_key] = old_timeout
        if old_model is None:
            os.environ.pop(model_key, None)
        else:
            os.environ[model_key] = old_model
        if old_retry_enabled is None:
            os.environ.pop(retry_enabled_key, None)
        else:
            os.environ[retry_enabled_key] = old_retry_enabled

    assert frame.source == "ai_structured_extraction"
    assert len(ai_service.calls) == 2
    assert ai_service.calls[0]["timeout"] == 11.0
    assert ai_service.calls[1]["timeout"] == 7.0
    assert ai_service.calls[1]["model_name"] == "fallback-test-model"
    assert ai_service.calls[0]["disable_retry"] is True
    assert ai_service.calls[1]["disable_retry"] is True


def test_ai_semantic_extraction_parse_observation_normalizes_residence_city_alias():
    observation = AISemanticExtractionService._parse_ai_observation(
        {
            "field": "residenceCity",
            "value": "深圳",
            "normalized_value": "深圳",
            "scope": "self",
            "owner": "self",
            "confidence": 0.9,
            "write_mode": "direct_write",
            "source": "ai_semantic_extraction",
        }
    )

    assert observation is not None
    assert observation.field == "location"
    assert observation.normalized_value == "深圳"
    assert observation.scope == "self"


def test_ai_semantic_extraction_parse_observation_normalizes_residence_alias():
    observation = AISemanticExtractionService._parse_ai_observation(
        {
            "field": "residence",
            "value": "深圳",
            "normalized_value": "深圳",
            "scope": "self",
            "owner": "self",
            "confidence": 0.9,
            "write_mode": "direct_write",
            "source": "ai_semantic_extraction",
        }
    )

    assert observation is not None
    assert observation.field == "location"
    assert observation.normalized_value == "深圳"
    assert observation.scope == "self"


def test_ai_semantic_extraction_parse_observation_falls_back_to_value_when_normalized_missing():
    observation = AISemanticExtractionService._parse_ai_observation(
        {
            "field": "location",
            "value": "深圳",
            "normalized_value": "",
            "scope": "self",
            "owner": "self",
            "confidence": 0.9,
            "write_mode": "direct_write",
            "source": "ai_semantic_extraction",
        }
    )

    assert observation is not None
    assert observation.field == "location"
    assert observation.normalized_value == "深圳"
    assert observation.evidence_text == "深圳"


def test_ai_semantic_extraction_normalize_field_name_maps_dating_requirement_alias():
    normalized = AISemanticExtractionService._normalize_ai_field_name("交友需求")

    assert normalized == "partner_requirement"


def test_ai_semantic_extraction_attempt_plan_applies_blocking_cap():
    timeout_key = "UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS"
    cap_key = "UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS"
    retry_enabled_key = "UNIFIED_TURN_SYNC_AI_RETRY_ENABLED"
    old_timeout = os.environ.get(timeout_key)
    old_cap = os.environ.get(cap_key)
    old_retry_enabled = os.environ.get(retry_enabled_key)
    os.environ[timeout_key] = "60"
    os.environ[cap_key] = "18"
    os.environ[retry_enabled_key] = "0"
    try:
        attempts = AISemanticExtractionService._build_ai_attempt_plan(None)  # noqa: SLF001
    finally:
        if old_timeout is None:
            os.environ.pop(timeout_key, None)
        else:
            os.environ[timeout_key] = old_timeout
        if old_cap is None:
            os.environ.pop(cap_key, None)
        else:
            os.environ[cap_key] = old_cap
        if old_retry_enabled is None:
            os.environ.pop(retry_enabled_key, None)
        else:
            os.environ[retry_enabled_key] = old_retry_enabled

    assert len(attempts) == 1
    assert attempts[0]["timeout"] == 18.0


def test_ai_semantic_extraction_attempt_plan_keeps_explicit_timeout_override_when_cap_not_enforced():
    timeout_key = "UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS"
    cap_key = "UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS"
    retry_enabled_key = "UNIFIED_TURN_SYNC_AI_RETRY_ENABLED"
    old_timeout = os.environ.get(timeout_key)
    old_cap = os.environ.get(cap_key)
    old_retry_enabled = os.environ.get(retry_enabled_key)
    os.environ[timeout_key] = "60"
    os.environ[cap_key] = "18"
    os.environ[retry_enabled_key] = "0"
    try:
        attempts = AISemanticExtractionService._build_ai_attempt_plan(45.0)  # noqa: SLF001
    finally:
        if old_timeout is None:
            os.environ.pop(timeout_key, None)
        else:
            os.environ[timeout_key] = old_timeout
        if old_cap is None:
            os.environ.pop(cap_key, None)
        else:
            os.environ[cap_key] = old_cap
        if old_retry_enabled is None:
            os.environ.pop(retry_enabled_key, None)
        else:
            os.environ[retry_enabled_key] = old_retry_enabled

    assert len(attempts) == 1
    assert attempts[0]["timeout"] == 45.0


def test_ai_semantic_extraction_attempt_plan_caps_explicit_timeout_when_mainline_cap_enforced():
    timeout_key = "UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS"
    cap_key = "UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS"
    retry_enabled_key = "UNIFIED_TURN_SYNC_AI_RETRY_ENABLED"
    old_timeout = os.environ.get(timeout_key)
    old_cap = os.environ.get(cap_key)
    old_retry_enabled = os.environ.get(retry_enabled_key)
    os.environ[timeout_key] = "60"
    os.environ[cap_key] = "18"
    os.environ[retry_enabled_key] = "0"
    try:
        attempts = AISemanticExtractionService._build_ai_attempt_plan(45.0, enforce_blocking_cap=True)  # noqa: SLF001
    finally:
        if old_timeout is None:
            os.environ.pop(timeout_key, None)
        else:
            os.environ[timeout_key] = old_timeout
        if old_cap is None:
            os.environ.pop(cap_key, None)
        else:
            os.environ[cap_key] = old_cap
        if old_retry_enabled is None:
            os.environ.pop(retry_enabled_key, None)
        else:
            os.environ[retry_enabled_key] = old_retry_enabled

    assert len(attempts) == 1
    assert attempts[0]["timeout"] == 18.0


def test_ai_semantic_extraction_transport_failures_open_circuit_breaker_and_skip_following_calls():
    class _TimeoutAIService:
        def __init__(self):
            self.calls = 0

        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            self.calls += 1
            raise AIServiceException("AI 服务响应超时（45.0秒）")

    breaker_enabled_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_ENABLED"
    breaker_threshold_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_THRESHOLD"
    breaker_cooldown_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS"
    old_enabled = os.environ.get(breaker_enabled_key)
    old_threshold = os.environ.get(breaker_threshold_key)
    old_cooldown = os.environ.get(breaker_cooldown_key)
    os.environ[breaker_enabled_key] = "1"
    os.environ[breaker_threshold_key] = "2"
    os.environ[breaker_cooldown_key] = "180"
    semantic_service = SimpleNamespace(_extract_deterministic_profile_fields=lambda message: {})
    ai_service = _TimeoutAIService()
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=ai_service)
    snapshot = TurnInputSnapshot(
        user_message="94年，深圳南山，微信联系我13426689341",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="opening", subtype="dense_intro", confidence=0.9)
    AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
    try:
        first_frame = asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=2.0,
            )
        )
        second_frame = asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=2.0,
            )
        )
        third_frame = asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=2.0,
            )
        )
    finally:
        AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
        if old_enabled is None:
            os.environ.pop(breaker_enabled_key, None)
        else:
            os.environ[breaker_enabled_key] = old_enabled
        if old_threshold is None:
            os.environ.pop(breaker_threshold_key, None)
        else:
            os.environ[breaker_threshold_key] = old_threshold
        if old_cooldown is None:
            os.environ.pop(breaker_cooldown_key, None)
        else:
            os.environ[breaker_cooldown_key] = old_cooldown

    assert any("ai_semantic_status=failed:request_failed" in str(note) for note in first_frame.notes)
    assert any("ai_semantic_status=failed:request_failed" in str(note) for note in second_frame.notes)
    assert any("ai_semantic_status=skipped:circuit_open" in str(note) for note in third_frame.notes)
    assert ai_service.calls == 2


def test_ai_semantic_extraction_parse_failure_does_not_open_circuit_breaker():
    class _LooseAIService:
        def __init__(self):
            self.calls = 0

        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            self.calls += 1
            return "我大概听懂了，但先解释一下"

    breaker_enabled_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_ENABLED"
    breaker_threshold_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_THRESHOLD"
    old_enabled = os.environ.get(breaker_enabled_key)
    old_threshold = os.environ.get(breaker_threshold_key)
    os.environ[breaker_enabled_key] = "1"
    os.environ[breaker_threshold_key] = "2"
    semantic_service = SimpleNamespace(_extract_deterministic_profile_fields=lambda message: {})
    ai_service = _LooseAIService()
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=ai_service)
    snapshot = TurnInputSnapshot(
        user_message="94年，深圳南山，微信联系我13426689341",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="opening", subtype="dense_intro", confidence=0.9)
    AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
    try:
        asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=2.0,
            )
        )
        asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=2.0,
            )
        )
    finally:
        skip_status = AISemanticExtractionService._current_sync_ai_skip_status()  # noqa: SLF001
        AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
        if old_enabled is None:
            os.environ.pop(breaker_enabled_key, None)
        else:
            os.environ[breaker_enabled_key] = old_enabled
        if old_threshold is None:
            os.environ.pop(breaker_threshold_key, None)
        else:
            os.environ[breaker_threshold_key] = old_threshold

    assert ai_service.calls == 2
    assert skip_status is None


def test_ai_semantic_extraction_passes_reasoning_effort_to_ai_service():
    class _RecordingAIService:
        def __init__(self):
            self.calls = []

        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            self.calls.append(dict(kwargs or {}))
            return (
                '{"primary_domain":"profile","acts":[],"user_questions":[],"field_observations":['
                '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self",'
                '"evidence_text":"在编教师","evidence_span":"在编教师","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
                '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
            )

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    ai_service = _RecordingAIService()
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=ai_service)
    snapshot = TurnInputSnapshot(
        user_message="在编教师",
        last_response="你现在是做哪方面工作的呀？",
        message_count=3,
        prompt_state={"asked_fields": ["occupation"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="profile_answer", subtype="single_slot_answer", confidence=0.9)

    env_key = "UNIFIED_TURN_SYNC_AI_REASONING_EFFORT"
    old_env = os.environ.get(env_key)
    os.environ[env_key] = "medium"
    try:
        frame = asyncio.run(
            service.extract(
                snapshot=snapshot,
                fallback_result=fallback,
                enable_ai=True,
                ai_timeout_seconds=5.0,
            )
        )
    finally:
        if old_env is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = old_env

    assert frame.source == "ai_structured_extraction"
    assert len(ai_service.calls) == 1
    assert ai_service.calls[0]["reasoning_effort"] == "medium"


def test_ai_semantic_extraction_build_frame_from_slim_payload_items():
    service = AISemanticExtractionService(semantic_service=SimpleNamespace(), ai_service=None)
    frame = service._build_frame_from_slim_payload(  # noqa: SLF001
        {
            "primary_domain": "mixed",
            "items": [
                {
                    "field": "education",
                    "value": "本科",
                    "scope": "self",
                    "write_mode": "direct_write",
                    "confidence": 0.93,
                },
                {
                    "field": "身高",
                    "value": "180cm及以上",
                    "scope": "partner",
                    "write_mode": "direct_write",
                    "confidence": 0.91,
                },
            ],
        }
    )

    assert frame is not None
    assert frame.source == "ai_structured_extraction"
    observations = {(obs.field, obs.scope): obs for obs in frame.field_observations}
    assert ("education", "self") in observations
    assert ("partner_pref_height", "partner") in observations


def test_ai_semantic_extraction_build_frame_from_ai_payload_accepts_items_shape():
    service = AISemanticExtractionService(semantic_service=SimpleNamespace(), ai_service=None)
    frame = service._build_frame_from_ai_payload(  # noqa: SLF001
        {
            "primary_domain": "profile",
            "items": [
                {
                    "field": "occupation",
                    "value": "在编教师",
                    "scope": "self",
                    "write_mode": "direct_write",
                    "confidence": 0.95,
                }
            ],
        }
    )

    assert frame is not None
    assert frame.primary_domain == "profile"
    assert len(frame.field_observations) == 1
    assert frame.field_observations[0].field == "occupation"
    assert frame.field_observations[0].normalized_value == "在编教师"


def test_ai_semantic_extraction_prefers_richer_partner_requirement_over_weak_seed():
    extraction_service = SimpleNamespace(
        _extract_partner_preference_subslots=lambda message: {"partner_pref_age": "90后"},
        _resolve_partner_requirement_from_message=lambda message, allow_legacy_fallback=True, prefer_structured=True: "90后工作稳定就行，身高180cm以上",
        _compose_partner_requirement_from_subslots=lambda subslots, raw: "90后工作稳定就行，身高180cm以上",
    )
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {"partner_requirement": "身高180cm以上"},
        _extract_partner_gender_preference=lambda message: "男",
        chat_service=SimpleNamespace(extraction_service=extraction_service),
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=None)

    fields = service._extract_deterministic_fields(  # noqa: SLF001
        "找对象 女生找男朋友，找起码180+，90后工作稳定就行",
        prompt_state={},
    )

    assert fields["partner_requirement"] == "90后工作稳定就行，身高180cm以上"
    assert fields["partner_pref_age"] == "90后"


def test_ai_semantic_extraction_falls_back_when_ai_returns_empty_items():
    class _EmptyAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return '{"primary_domain":"profile","items":[]}'

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_EmptyAIService())
    snapshot = TurnInputSnapshot(
        user_message="在编教师",
        last_response="你现在是做哪方面工作的呀？",
        message_count=3,
        prompt_state={"asked_fields": ["occupation"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"occupation": "在编教师"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    assert frame.source != "ai_structured_extraction"
    assert any(str(getattr(obs, "field", "") or "") == "occupation" for obs in frame.field_observations)


def test_ai_semantic_extraction_extract_accepts_items_shape_without_falling_back():
    class _ItemsAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return '{"primary_domain":"profile","items":[{"field":"occupation","scope":"self","value":"在编教师"}]}'

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_ItemsAIService())
    snapshot = TurnInputSnapshot(
        user_message="在编教师",
        last_response="你现在是做哪方面工作的呀？",
        message_count=3,
        prompt_state={"asked_fields": ["occupation"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"occupation": "在编教师"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    assert frame.source == "ai_structured_extraction"
    assert any(str(getattr(obs, "field", "") or "") == "occupation" for obs in frame.field_observations)
    assert any("ai_semantic_status=success:json_frame" in str(note) for note in frame.notes)


def test_ai_semantic_extraction_supplements_missing_fields_from_fallback_projection_on_ai_success():
    class _OccupationOnlyAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return '{"primary_domain":"profile","items":[{"field":"occupation","scope":"self","value":"在编教师"}]}'

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_OccupationOnlyAIService())
    snapshot = TurnInputSnapshot(
        user_message="深圳龙华在编教师，微信是abc12345",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={"asked_fields": [], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"occupation": "在编教师", "location": "深圳龙华", "wechat": "abc12345"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    assert frame.source == "ai_structured_extraction"
    observations = {(obs.field, obs.scope): obs for obs in frame.field_observations}
    assert observations[("occupation", "self")].normalized_value == "在编教师"
    assert observations[("location", "self")].normalized_value == "深圳龙华"
    assert observations[("wechat", "contact")].normalized_value == "abc12345"
    assert any("fallback_projection_merge=added:" in str(note) for note in frame.notes)


def test_ai_semantic_extraction_keeps_ai_field_when_fallback_has_same_field():
    class _AIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return '{"primary_domain":"profile","items":[{"field":"occupation","scope":"self","value":"产品经理","confidence":0.95}]}'

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_AIService())
    snapshot = TurnInputSnapshot(
        user_message="做产品的，也在深圳",
        last_response="你目前是做哪方面工作的？",
        message_count=2,
        prompt_state={"asked_fields": ["occupation"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"occupation": "产品", "location": "深圳"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    occupation_observations = [
        obs for obs in frame.field_observations if str(getattr(obs, "field", "") or "") == "occupation"
    ]
    assert frame.source == "ai_structured_extraction"
    assert len(occupation_observations) == 1
    assert occupation_observations[0].normalized_value == "产品经理"
    assert any(str(getattr(obs, "field", "") or "") == "location" for obs in frame.field_observations)


def test_ai_semantic_extraction_allows_fallback_refinement_to_correct_ai_same_field():
    class _AIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return (
                '{"primary_domain":"profile","items":['
                '{"field":"location","scope":"self","value":"深圳","confidence":0.90},'
                '{"field":"education","scope":"self","value":"硕士","confidence":0.92}'
                ']}'
            )

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_AIService())
    snapshot = TurnInputSnapshot(
        user_message="资料如上",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="dense_intro",
        resolved_slots={"location": "深圳南山", "education": "港硕"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    observations = {
        str(getattr(obs, "field", "") or "").strip(): str(getattr(obs, "normalized_value", "") or "").strip()
        for obs in frame.field_observations
        if str(getattr(obs, "scope", "") or "").strip() == "self"
    }
    assert frame.source == "ai_structured_extraction"
    assert observations["location"] == "深圳南山"
    assert observations["education"] == "港硕"
    assert any("fallback_projection_merge=added:" in str(note) for note in frame.notes)
    assert any("fallback_projection_refinement=candidates:" in str(note) for note in frame.notes)


def test_ai_semantic_extraction_allows_authoritative_direct_observation_to_correct_ai_occupation():
    semantic_service = TurnUnderstandingService(
        SimpleNamespace(
            extraction_service=ExtractionService(SimpleNamespace()),
            user_question_service=SimpleNamespace(detect_quick_faq_intent=lambda message: None),
            expectation_service=SimpleNamespace(is_matching_timeline_question=lambda message: False),
        )
    )

    class _AIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return (
                '{"primary_domain":"profile","items":['
                '{"field":"occupation","scope":"self","value":"外贸行业工作","confidence":0.90}'
                ']}'
            )

    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_AIService())
    snapshot = TurnInputSnapshot(
        user_message="94年，湖南女生在深圳南山，外贸行业工作，港硕",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="dense_intro",
        resolved_slots={"occupation": "外贸"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    observations = {
        str(getattr(obs, "field", "") or "").strip(): str(getattr(obs, "normalized_value", "") or "").strip()
        for obs in frame.field_observations
        if str(getattr(obs, "scope", "") or "").strip() == "self"
    }
    assert frame.source == "ai_structured_extraction"
    assert observations["occupation"] == "外贸"
    assert any("fallback_projection_refinement=candidates:" in str(note) for note in frame.notes)


def test_ai_semantic_extraction_merges_direct_evidence_to_correct_ai_age_and_contact_channel():
    semantic_service = TurnUnderstandingService(
        SimpleNamespace(
            extraction_service=ExtractionService(SimpleNamespace()),
            user_question_service=SimpleNamespace(detect_quick_faq_intent=lambda message: None),
            expectation_service=SimpleNamespace(is_matching_timeline_question=lambda message: False),
        )
    )

    class _WrongAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return (
                '{"primary_domain":"mixed","items":['
                '{"field":"age","scope":"self","value":"30","confidence":0.93},'
                '{"field":"location","scope":"self","value":"深圳","confidence":0.90},'
                '{"field":"education","scope":"self","value":"硕士","confidence":0.91},'
                '{"field":"occupation","scope":"self","value":"外贸行业工作","confidence":0.90},'
                '{"field":"phone","scope":"contact","value":"13426689341","confidence":0.96}'
                ']}'
            )

    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_WrongAIService())
    snapshot = TurnInputSnapshot(
        user_message="94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，到时候可以微信联系我13426689341",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="opening", subtype="dense_intro", confidence=0.9)

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    observations = {
        str(getattr(item, "field", "") or "").strip(): str(getattr(item, "normalized_value", "") or "").strip()
        for item in frame.field_observations
        if str(getattr(item, "scope", "") or "").strip() in {"self", "contact"}
    }

    assert frame.source == "ai_structured_extraction"
    assert observations["age_label"] == "94年"
    assert observations["age"] == "32"
    assert observations["location"] == "深圳南山"
    assert observations["education"] == "港硕"
    assert observations["occupation"] == "外贸"
    assert observations["wechat"] == "13426689341"
    assert "phone" not in observations


def test_ai_semantic_extraction_logs_failure_stage_for_non_json_output(caplog):
    class _LooseAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return "我理解成自我介绍加联系方式了，但我先解释一下"

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_LooseAIService())
    snapshot = TurnInputSnapshot(
        user_message="94年，深圳南山，微信联系我13426689341",
        last_response="可以留个微信吗？",
        message_count=3,
        prompt_state={"asked_fields": ["contact"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="contact_answer",
        subtype="contact_provided",
        resolved_slots={"wechat": "13426689341"},
        confidence=0.9,
    )

    caplog.set_level(logging.INFO)
    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    invalid_logs = [record.message for record in caplog.records if "invalid_frame" in record.message]
    fallback_logs = [record.message for record in caplog.records if "fallback_to_projection" in record.message]
    assert any("parse_stage=non_json_output" in message for message in invalid_logs)
    assert any("final_stage=non_json_output" in message for message in fallback_logs)
    assert "ai_semantic_status=failed:non_json_output" in frame.notes
    observations = {
        str(getattr(item, "field", "") or "").strip(): str(getattr(item, "normalized_value", "") or "").strip()
        for item in frame.field_observations
        if str(getattr(item, "scope", "") or "").strip() in {"self", "contact"}
    }
    assert observations["wechat"] == "13426689341"


def test_ai_semantic_extraction_fallback_projection_merges_direct_evidence_for_precise_fields():
    semantic_service = TurnUnderstandingService(
        SimpleNamespace(
            extraction_service=ExtractionService(SimpleNamespace()),
            user_question_service=SimpleNamespace(detect_quick_faq_intent=lambda message: None),
            expectation_service=SimpleNamespace(is_matching_timeline_question=lambda message: False),
        )
    )

    class _LooseAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return "我大概听懂了，但先解释一下"

    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_LooseAIService())
    snapshot = TurnInputSnapshot(
        user_message="94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，到时候可以微信联系我13426689341",
        last_response="方便简单说下自己的情况吗？",
        message_count=1,
        prompt_state={},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="dense_intro",
        resolved_slots={"location": "深圳", "education": "硕士"},
        confidence=0.9,
    )

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    observations = {
        str(getattr(item, "field", "") or "").strip(): str(getattr(item, "normalized_value", "") or "").strip()
        for item in frame.field_observations
        if str(getattr(item, "scope", "") or "").strip() in {"self", "contact"}
    }

    assert frame.source != "ai_structured_extraction"
    assert observations["age_label"] == "94年"
    assert observations["location"] == "深圳南山"
    assert observations["education"] == "港硕"
    assert observations["occupation"] == "外贸"
    assert observations["wechat"] == "13426689341"


def test_ai_semantic_extraction_recovers_truncated_json_like_payload():
    class _TruncatedAIService:
        async def generate_response(self, *args, **kwargs):  # noqa: ARG002
            return (
                '{ "userInfo": { "birthYear": "1994年", "gender": "女", "currentLocation": "深圳南山", '
                '"education": "港硕", "industry": "外贸行业工作" }, "contactInfo": { "wechat": "abc123456" }'
            )

    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=_TruncatedAIService())
    snapshot = TurnInputSnapshot(
        user_message="94年，深圳南山，港硕，外贸行业工作，微信abc123456",
        last_response="方便留个微信吗？",
        message_count=2,
        prompt_state={"asked_fields": ["contact"], "side_fields": []},
        user_profile=SimpleNamespace(),
    )
    fallback = TurnUnderstandingResult(primary_turn_type="contact_answer", subtype="contact_provided", confidence=0.9)

    frame = asyncio.run(
        service.extract(
            snapshot=snapshot,
            fallback_result=fallback,
            enable_ai=True,
            ai_timeout_seconds=2.0,
        )
    )

    observations = {
        (str(getattr(item, "field", "") or ""), str(getattr(item, "normalized_value", "") or "")): item
        for item in frame.field_observations
    }
    assert frame.source == "ai_structured_extraction"
    assert any(
        key[0] == "age_label" and key[1] in {"1994年", "94年"}
        for key in observations
    )
    assert ("location", "深圳南山") in observations
    assert ("education", "港硕") in observations
    assert ("occupation", "外贸行业工作") in observations
    assert ("wechat", "abc123456") in observations


def test_field_update_policy_marital_status_semantic_equivalence_does_not_hold_for_confirmation():
    service = FieldUpdatePolicyService()
    frame = TurnSemanticFrame(
        version="v1",
        source="ai_structured_extraction",
        primary_domain="profile",
    )
    accepted = AcceptedField(
        field="marital_status",
        value="单身",
        normalized_value="单身",
        scope="self",
        evidence_text="单身呢",
        confidence=0.95,
        acceptance_reason="direct_write",
        update_action="accept_as_new",
        source_channel="ai",
    )

    action = service._resolve_action(  # noqa: SLF001
        field=accepted,
        current_value="未婚单身",
        frame=frame,
    )

    assert action == "accept_as_refinement"


def test_field_permission_decide_keeps_partner_requirement_for_compound_self_and_preference_text():
    layer = FieldPermissionLayer()
    result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={"occupation": "在编教师", "partner_requirement": "成熟稳重，多金，身高180+"},
        confidence=0.92,
    )

    permission = layer.decide(
        turn_input=_make_input("在编教师，喜欢成熟稳重，多金，身高180+"),
        semantic_result=result,
        reply_act_result=ReplyActClassificationResult(reply_act="direct_answer", confidence=0.9, reason="test"),
        question_state={
            "asked_fields": ["occupation"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        },
    )

    assert permission.allowed_scope == "mixed"
    assert permission.allow_mixed_answer is True
    assert "partner_requirement" in permission.allowed_fields
    assert "partner_requirement" not in permission.blocked_fields
