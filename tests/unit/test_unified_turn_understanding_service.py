from __future__ import annotations

import asyncio
import logging
import os
import time
from types import SimpleNamespace

from src.modules.conversation.domain.turn_understanding_models import SlotCandidate, TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.conversation_understanding.domain.ai_semantic_extraction_service import AISemanticExtractionService
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


class _StubAIService:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0
        self.last_kwargs = {}

    async def generate_response(self, *args, **kwargs):  # noqa: ARG002
        self.calls += 1
        self.last_kwargs = dict(kwargs or {})
        return self.response


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


def test_ai_semantic_extraction_deterministic_fields_no_longer_backfills_partner_requirement_via_simple_helper():
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
        _extract_simple_partner_requirement=lambda message: "温柔",
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=None)

    fields = service._extract_deterministic_fields("温柔吧")  # noqa: SLF001

    assert "partner_requirement" not in fields


def test_ai_semantic_extraction_deterministic_fields_no_longer_backfills_partner_requirement_via_compact_regex():
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=None)

    fields = service._extract_deterministic_fields("找成熟稳重的")  # noqa: SLF001

    assert "partner_requirement" not in fields


def test_ai_semantic_extraction_calls_ai_service_with_disable_retry_enabled():
    semantic_service = SimpleNamespace(
        _extract_deterministic_profile_fields=lambda message: {},
    )
    ai_service = _StubAIService(
        '{"primary_domain":"profile","acts":[],"user_questions":[],"field_observations":['
        '{"field":"location","value":"深圳","normalized_value":"深圳","scope":"self","owner":"self","evidence_text":"我在深圳","evidence_span":"深圳","confidence":0.95,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.9}'
    )
    service = AISemanticExtractionService(semantic_service=semantic_service, ai_service=ai_service)
    fallback = TurnUnderstandingResult(primary_turn_type="opening", subtype="greeting", confidence=0.7)
    snapshot = SimpleNamespace(
        user_message="我在深圳",
        last_response="",
        prompt_state={},
        user_profile=SimpleNamespace(),
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
    assert ai_service.calls == 1
    assert ai_service.last_kwargs.get("disable_retry") is True


def test_unified_understanding_commits_self_sex_for_mixed_intro_with_gender_preference():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就"
            )
        )
    )

    accepted_fields = list(getattr(getattr(result, "persistence_plan", None), "accepted_fields", []) or [])
    accepted_by_name = {
        str(getattr(field, "field", "") or "").strip(): field
        for field in accepted_fields
        if str(getattr(field, "field", "") or "").strip()
    }

    assert "sex" in accepted_by_name
    assert str(getattr(accepted_by_name["sex"], "normalized_value", "") or "") == "女"
    assert str(getattr(accepted_by_name["sex"], "acceptance_reason", "") or "") == "explicit_self_marker"


def test_unified_understanding_fallback_dense_intro_extracts_chunked_partner_and_self_context():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，E人，感情经历简单，喜欢做饭旅游，"
                "原生家庭幸福美满关系简单，期待遇见同在深圳工作发展90后男生，积极阳光，三观正，到时候可以微信联系我13426689341"
            )
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["occupation"] == "外贸"
    assert result.resolved_slots["partner_pref_age"] == "90后"
    assert result.resolved_slots["partner_pref_location"] == "深圳"
    assert "partner_requirement" in result.resolved_slots
    assert "积极阳光" in result.resolved_slots["partner_requirement"]
    assert "三观正" in result.resolved_slots["partner_requirement"]
    assert "做饭旅游" not in result.resolved_slots["partner_requirement"]
    assert "原生家庭" not in result.resolved_slots["partner_requirement"]

    frame = getattr(result, "semantic_frame", None)
    assert frame is not None
    observations = {(item.field, item.scope): item for item in (frame.field_observations or [])}
    assert ("partner_requirement", "partner") in observations
    assert ("partner_pref_age", "partner") in observations
    assert ("partner_pref_location", "partner") in observations
    notes = list(getattr(frame, "notes", []) or [])
    assert any(str(note).startswith("partner_summary=") for note in notes)
    assert any(str(note).startswith("soft_profile_summary=") for note in notes)


def test_unified_understanding_does_not_leak_partner_age_bucket_into_self_profile():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就这么多了。"
            )
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["monthly_income"] == "一年18左右"
    assert result.resolved_slots["partner_pref_age"] == "90后"
    assert result.resolved_slots["partner_pref_height"] == "身高180cm以上"
    assert result.resolved_slots["partner_requirement"] == "90后工作稳定就行，身高180cm以上"
    assert "age" not in result.resolved_slots
    assert "age_label" not in result.resolved_slots


def test_unified_understanding_does_not_treat_hometown_as_self_occupation():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "可以啊 96深圳坪山在编教师，湖北人 不高150，105左右，想找能接受身高差，最好深圳有房有车，一样本科或者以上，不要92暂时就这么多了有合适不。"
            )
        )
    )

    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["age_label"] == "96年"
    assert result.field_derivations["age_label"] == "96年"
    assert result.resolved_slots["partner_pref_location"] == "深圳"
    assert "湖北人" not in set(str(value) for value in result.resolved_slots.values())
    assert "暂时就这么多了有合适不" not in result.resolved_slots["partner_requirement"]


def test_unified_understanding_keeps_partner_stability_preference_without_tail_noise():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "98年女生，本科学历，从事外贸工作，未婚单身，年新在20左右，深圳本地，想着90后男生，喜欢运动，情绪稳定就行，其他没有要求，也可以加我微信联系 13423674892微信和电话同号。"
            )
        )
    )

    assert result.resolved_slots["partner_pref_age"] == "90后"
    assert result.resolved_slots["wechat"] == "13423674892"
    assert result.resolved_slots["phone"] == "13423674892"
    assert "情绪稳定" in result.resolved_slots["partner_requirement"]
    assert "其他没有要求" not in result.resolved_slots["partner_requirement"]
    assert "加我微信联系" not in result.resolved_slots["partner_requirement"]


def test_unified_understanding_fallback_compact_intro_commits_nurse_occupation_and_age():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地。"
            )
        )
    )

    assert result.resolved_slots["occupation"] == "护士"
    assert result.resolved_slots["age_label"] == "90年"
    assert result.field_derivations["age_label"] == "90年"
    assert result.resolved_slots["partner_pref_location"] == "深圳"


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


def test_unified_understanding_pure_faq_turn_blocks_profile_slot_writeback():
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
                "你们是机构吗，资源怎么样啊",
                last_response="你好呀，方便简单了解下吗？",
            )
        )
    )

    assert result.resolved_slots == {}


def test_unified_understanding_keeps_profile_and_contact_slots_on_mixed_faq_message():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="faq_concern",
            subtype="fee",
            resolved_slots={"occupation": "在编教师", "location": "深圳龙华", "phone": "13526783627"},
            confidence=0.9,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "深圳龙华在编教师，可以直接电话联系13526783627，怎么收费呢先了解下",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["location"] == "深圳龙华"
    assert result.resolved_slots["phone"] == "13526783627"


def test_unified_understanding_direct_semantic_extraction_recovers_mixed_long_intro_fields():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"phone": "13526783627"},
            confidence=0.93,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    semantic_frame = getattr(result, "semantic_frame", None)
    assert semantic_frame is not None
    assert semantic_frame.source == "hybrid_semantic_projection"

    observations = {(item.field, item.scope): item for item in semantic_frame.field_observations}
    assert ("location", "self") in observations
    assert observations[("location", "self")].normalized_value == "深圳龙华"
    assert ("occupation", "self") in observations
    assert observations[("occupation", "self")].normalized_value == "在编教师"
    assert observations[("occupation", "self")].source == "semantic_explicit_self_marker"
    assert ("sex", "self") in observations
    assert observations[("sex", "self")].normalized_value == "女"
    assert observations[("sex", "self")].source == "semantic_explicit_self_marker"
    assert ("height", "self") in observations
    assert observations[("height", "self")].normalized_value == 165
    assert ("weight", "self") in observations
    assert observations[("weight", "self")].normalized_value == 104
    assert ("phone", "contact") in observations
    assert observations[("phone", "contact")].normalized_value == "13526783627"
    assert ("partner_requirement", "partner") in observations
    assert observations[("partner_requirement", "partner")].normalized_value == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"
    assert ("partner_pref_industry", "partner") not in observations
    assert any(question.topic == "pricing" for question in semantic_frame.user_questions)

    assert result.resolved_slots["location"] == "深圳龙华"
    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["height"] == "165"
    assert result.resolved_slots["weight"] == "104"
    assert result.resolved_slots["phone"] == "13526783627"
    assert result.resolved_slots["partner_requirement"] == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"


def test_sync_ai_semantic_enables_for_opening_dense_intro_with_self_income_signal():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="matchmaking_intent",
        resolved_slots={
            "location": "深圳",
            "education": "本科",
            "monthly_income": "18万左右",
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="mixed_answer")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is True
    assert reason == "sync_dense_intro"


def test_sync_ai_semantic_skips_dense_intro_when_rule_coverage_is_already_complete():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，期待遇见同在深圳工作发展90后男生，积极阳光，三观正，到时候可以微信联系我13426689341"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="dense_intro",
        resolved_slots={
            "sex": "女",
            "age_label": "94年",
            "location": "深圳南山",
            "education": "港硕",
            "occupation": "外贸",
            "wechat": "13426689341",
            "partner_requirement": "同在深圳工作发展90后男生，积极阳光，三观正",
            "partner_pref_location": "深圳",
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="preference_statement")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is False
    assert reason == "dense_intro_async_backfill_only"


def test_sync_ai_semantic_skips_dense_intro_when_long_intro_has_strong_self_and_contact_coverage():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，E人，感情经历简单，喜欢做饭旅游，"
        "原生家庭幸福美满关系简单，期待遇见同在深圳工作发展90后男生，积极阳光，三观正，到时候可以微信联系我13426689341。"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={
            "age": "32",
            "age_label": "94年",
            "location": "深圳",
            "education": "硕士",
            "occupation": "外贸",
            "sex": "女",
            "wechat": "13426689341",
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="preference_statement")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is False
    assert reason == "dense_intro_async_backfill_only"


def test_sync_ai_semantic_keeps_dense_intro_sync_when_message_contains_service_question():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费呢先了解下"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="opening",
        subtype="dense_intro",
        resolved_slots={
            "sex": "女",
            "location": "深圳龙华",
            "occupation": "在编教师",
            "phone": "13526783627",
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="direct_answer")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is True
    assert reason == "sync_dense_intro"


def test_sync_ai_semantic_skips_dense_intro_when_service_question_already_has_rich_profile_coverage():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，"
        "不要92可以直接电话联系这边13526783627对啦怎么收费呢先了解一下。"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="single_slot_answer",
        resolved_slots={"phone": "13526783627"},
        slot_candidates={
            "education": SlotCandidate(value="本科", confidence=0.9, source="test_stub", source_text="一样本科"),
            "occupation": SlotCandidate(value="在编教师", confidence=0.9, source="test_stub", source_text="在编女教师"),
            "phone": SlotCandidate(value="13526783627", confidence=0.99, source="test_stub", source_text="13526783627"),
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="direct_answer")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is False
    assert reason == "dense_intro_async_backfill_only"


def test_sync_ai_semantic_skips_dense_intro_when_textual_self_coverage_is_stable():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    turn_input = _make_input(
        "可以啊 96深圳坪山在编教师，湖北人 不高150，105左右，想找能接受身高差，最好深圳有房有车，"
        "一样本科或者以上，不要92暂时就这么多了有合适不。"
    )
    semantic_result = TurnUnderstandingResult(
        primary_turn_type="profile_answer",
        subtype="multi_slot_compound",
        resolved_slots={
            "location": "深圳坪山",
            "occupation": "在编教师",
            "partner_requirement": "学历本科及以上",
            "partner_pref_education": "学历本科及以上",
        },
        confidence=0.9,
    )
    reply_act_result = SimpleNamespace(reply_act="mixed_answer")
    turn_mode = service._resolve_turn_mode(  # noqa: SLF001
        turn_input=turn_input,
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
    )

    use_ai, reason = service._should_enable_sync_ai_semantic(  # noqa: SLF001
        turn_input=turn_input,
        question_state={},
        semantic_result=semantic_result,
        reply_act_result=reply_act_result,
        turn_mode=turn_mode,
    )

    assert turn_mode == "dense_intro"
    assert use_ai is False
    assert reason == "dense_intro_async_backfill_only"


def test_unified_understanding_rich_service_question_dense_intro_skips_sync_ai_call():
    semantic_service = TurnUnderstandingService(_StubChatService())
    ai_service = _StubAIService('{"primary_domain":"mixed","acts":[],"user_questions":[],"field_observations":[],"risk_flags":[],"boundaries":[],"confidence":0.9}')
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，"
                "不要92可以直接电话联系这边13526783627对啦怎么收费呢先了解一下。",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    assert ai_service.calls == 0
    assert getattr(result.semantic_frame, "source") == "hybrid_semantic_projection"
    assert result.primary_turn_type == "faq_concern"
    assert result.subtype == "pricing"
    assert result.resolved_slots["location"] == "深圳龙华"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["phone"] == "13526783627"


def test_unified_understanding_textual_dense_intro_skips_sync_ai_call():
    semantic_service = TurnUnderstandingService(_StubChatService())
    ai_service = _StubAIService('{"primary_domain":"mixed","acts":[],"user_questions":[],"field_observations":[],"risk_flags":[],"boundaries":[],"confidence":0.9}')
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "可以啊 96深圳坪山在编教师，湖北人 不高150，105左右，想找能接受身高差，最好深圳有房有车，"
                "一样本科或者以上，不要92暂时就这么多了有合适不。",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    assert ai_service.calls == 0
    assert getattr(result.semantic_frame, "source") == "hybrid_semantic_projection"
    assert result.resolved_slots["age_label"] == "96年"
    assert result.resolved_slots["location"] == "深圳坪山"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["education"] == "本科"
    assert "partner_requirement" in result.resolved_slots


def test_unified_understanding_keeps_partner_requirement_when_occupation_followup_receives_compound_answer():
    semantic_service = TurnUnderstandingService(_StubChatService())
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
                "在编教师，喜欢成熟稳重，多金，身高180+",
                last_response="你目前是做哪方面工作的？",
                user_profile=profile,
            )
        )
    )

    assert result.resolved_slots["occupation"] == "在编教师"
    assert "partner_requirement" in result.resolved_slots
    requirement = str(result.resolved_slots["partner_requirement"] or "")
    assert "成熟稳重" in requirement
    assert "多金" in requirement


def test_unified_understanding_keeps_age_and_preference_for_compound_preference_statement():
    semantic_service = TurnUnderstandingService(_StubChatService())
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["age"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "98年的，喜欢成熟稳重，多金，身高180+",
                last_response="你是哪一年出生的呀？",
                user_profile=profile,
            )
        )
    )

    assert "partner_requirement" in result.resolved_slots
    assert "age" in result.resolved_slots or "age_label" in result.resolved_slots


def test_unified_understanding_ai_semantic_extraction_can_override_legacy_contact_bias_with_force_ai():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"phone": "13526783627", "occupation": "在编教师"},
            confidence=0.93,
        )
    )
    ai_service = _StubAIService(
        '{"primary_domain":"faq","acts":["provide_contact","ask_service_question"],'
        '"user_questions":[{"topic":"pricing","question_text":"怎么收费呢先了解下","confidence":0.97}],'
        '"field_observations":[{"field":"phone","value":"13526783627","normalized_value":"13526783627","scope":"contact","owner":"self","evidence_text":"13526783627","evidence_span":"13526783627","confidence":0.99,"write_mode":"direct_write","source":"ai_semantic_extraction"}],'
        '"risk_flags":[],"boundaries":[],"confidence":0.97}'
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "深圳龙华在编教师，可以直接电话联系13526783627，怎么收费呢先了解下",
                last_response="方便简单说下自己的情况吗？",
            ),
            force_ai=True,
        )
    )

    assert ai_service.calls == 1
    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert any(question.topic == "pricing" for question in getattr(result, "semantic_frame").user_questions)


def test_unified_understanding_prefers_ai_semantic_extraction_when_force_ai():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"phone": "13526783627"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"mixed","acts":["provide_profile","provide_contact","ask_service_question"],'
        '"user_questions":[{"topic":"pricing","question_text":"怎么收费呢先了解下","confidence":0.96}],'
        '"field_observations":['
        '{"field":"location","value":"深圳龙华","normalized_value":"深圳龙华","scope":"self","owner":"self","evidence_text":"深圳龙华","evidence_span":"深圳龙华","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self","evidence_text":"在编女教师","evidence_span":"在编女教师","confidence":0.95,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"phone","value":"13526783627","normalized_value":"13526783627","scope":"contact","owner":"self","evidence_text":"13526783627","evidence_span":"13526783627","confidence":0.99,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费呢先了解下",
                last_response="方便简单说下自己的情况吗？",
            ),
            force_ai=True,
        )
    )

    semantic_frame = getattr(result, "semantic_frame", None)
    assert semantic_frame is not None
    assert semantic_frame.source == "ai_structured_extraction"
    assert result.resolved_slots["location"] == "深圳龙华"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["phone"] == "13526783627"


def test_unified_understanding_caps_dense_intro_sync_ai_timeout_in_mainline():
    dense_timeout_key = "UNIFIED_TURN_SYNC_AI_DENSE_INTRO_TIMEOUT_SECONDS"
    cap_key = "UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS"
    retry_enabled_key = "UNIFIED_TURN_SYNC_AI_RETRY_ENABLED"
    old_dense_timeout = os.environ.get(dense_timeout_key)
    old_cap = os.environ.get(cap_key)
    old_retry_enabled = os.environ.get(retry_enabled_key)
    os.environ[dense_timeout_key] = "45"
    os.environ[cap_key] = "12"
    os.environ[retry_enabled_key] = "0"

    semantic_service = TurnUnderstandingService(_StubChatService())
    ai_service = _StubAIService(
        '{"primary_domain":"mixed","acts":["provide_profile"],'
        '"user_questions":[],"field_observations":['
        '{"field":"occupation","value":"外贸","normalized_value":"外贸","scope":"self","owner":"self","evidence_text":"外贸行业工作","evidence_span":"外贸行业工作","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    try:
        result = asyncio.run(
            service.analyze(
                _make_input(
                    "深圳龙华在编女教师，可以直接电话联系这边13526783627，对啦怎么收费呢先了解下",
                    last_response="方便简单说下自己的情况吗？",
                )
            )
        )
    finally:
        if old_dense_timeout is None:
            os.environ.pop(dense_timeout_key, None)
        else:
            os.environ[dense_timeout_key] = old_dense_timeout
        if old_cap is None:
            os.environ.pop(cap_key, None)
        else:
            os.environ[cap_key] = old_cap
        if old_retry_enabled is None:
            os.environ.pop(retry_enabled_key, None)
        else:
            os.environ[retry_enabled_key] = old_retry_enabled

    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert ai_service.calls == 1
    assert ai_service.last_kwargs.get("timeout") == 12.0


def test_unified_understanding_skips_sync_ai_when_circuit_breaker_is_open():
    breaker_enabled_key = "UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_ENABLED"
    old_enabled = os.environ.get(breaker_enabled_key)
    os.environ[breaker_enabled_key] = "1"
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="dense_intro",
            confidence=0.9,
        )
    )
    ai_service = _StubAIService(
        '{"primary_domain":"profile","field_observations":[{"field":"occupation","value":"外贸","normalized_value":"外贸","scope":"self","owner":"self","evidence_text":"外贸行业工作","evidence_span":"外贸行业工作","confidence":0.9,"write_mode":"direct_write","source":"ai_semantic_extraction"}]}'
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)
    AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
    AISemanticExtractionService._SYNC_AI_CIRCUIT_BREAKER_STATE["open_until_monotonic"] = time.monotonic() + 30.0  # noqa: SLF001
    try:
        result = asyncio.run(
            service.analyze(
                _make_input(
                    "94年，湖南女生在深圳南山，外贸行业工作，港硕，微信联系我13426689341",
                    last_response="方便简单说下自己的情况吗？",
                )
            )
        )
    finally:
        AISemanticExtractionService._reset_sync_ai_circuit_breaker_state()  # noqa: SLF001
        if old_enabled is None:
            os.environ.pop(breaker_enabled_key, None)
        else:
            os.environ[breaker_enabled_key] = old_enabled

    semantic_frame = getattr(result, "semantic_frame", None)
    assert semantic_frame is not None
    assert semantic_frame.source != "ai_structured_extraction"
    assert any("ai_semantic_status=skipped:circuit_open" in str(note) for note in getattr(semantic_frame, "notes", []) or [])
    assert ai_service.calls == 0


def test_unified_understanding_ai_mixed_frame_reprojects_turn_type_and_priority():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"wechat": "abc123456"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"mixed","acts":["provide_profile","provide_contact"],'
        '"user_questions":[],"field_observations":['
        '{"field":"age_label","value":"94年","normalized_value":"94年","scope":"self","owner":"self","evidence_text":"94年","evidence_span":"94年","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"location","value":"深圳南山","normalized_value":"深圳南山","scope":"self","owner":"self","evidence_text":"深圳南山","evidence_span":"深圳南山","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"education","value":"硕士","normalized_value":"硕士","scope":"self","owner":"self","evidence_text":"港硕","evidence_span":"港硕","confidence":0.95,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"wechat","value":"abc123456","normalized_value":"abc123456","scope":"contact","owner":"self","evidence_text":"abc123456","evidence_span":"abc123456","confidence":0.99,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.96}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "94年，深圳南山，港硕，微信abc123456",
                last_response="方便加微信吗？",
                in_contact_flow=True,
            ),
            force_ai=True,
        )
    )

    assert result.primary_turn_type == "profile_answer"
    assert getattr(result, "semantic_frame").primary_domain == "mixed"
    assert result.priority_decision is not None
    assert result.priority_decision.primary_task == "core_profile_collection"
    assert "contact_record" not in result.priority_decision.suppressed_tasks


def test_unified_understanding_ai_success_allows_fallback_refinement_for_same_field_values():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="dense_intro",
            resolved_slots={"location": "深圳南山", "education": "港硕"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"profile","acts":["provide_profile"],'
        '"user_questions":[],"field_observations":['
        '{"field":"location","value":"深圳","normalized_value":"深圳","scope":"self","owner":"self","evidence_text":"深圳","evidence_span":"深圳","confidence":0.90,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"education","value":"硕士","normalized_value":"硕士","scope":"self","owner":"self","evidence_text":"硕士","evidence_span":"硕士","confidence":0.92,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "资料如上",
                last_response="方便简单说下自己的情况吗？",
            ),
            force_ai=True,
        )
    )

    semantic_frame = getattr(result, "semantic_frame", None)
    assert semantic_frame is not None
    assert semantic_frame.source == "ai_structured_extraction"
    observations = {(item.field, item.scope): item for item in semantic_frame.field_observations}
    assert observations[("location", "self")].normalized_value == "深圳南山"
    assert observations[("education", "self")].normalized_value == "港硕"
    assert any("fallback_projection_refinement=candidates:" in str(note) for note in getattr(semantic_frame, "notes", []) or [])
    assert result.resolved_slots["location"] == "深圳南山"
    assert result.resolved_slots["education"] == "港硕"


def test_unified_understanding_ai_success_allows_authoritative_direct_occupation_correction():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="opening",
            subtype="dense_intro",
            resolved_slots={"occupation": "外贸"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"profile","acts":["provide_profile"],'
        '"user_questions":[],"field_observations":['
        '{"field":"occupation","value":"外贸行业工作","normalized_value":"外贸行业工作","scope":"self","owner":"self","evidence_text":"外贸行业工作","evidence_span":"外贸行业工作","confidence":0.90,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "94年，湖南女生在深圳南山，外贸行业工作，港硕",
                last_response="方便简单说下自己的情况吗？",
            ),
            force_ai=True,
        )
    )

    semantic_frame = getattr(result, "semantic_frame", None)
    assert semantic_frame is not None
    assert semantic_frame.source == "ai_structured_extraction"
    observations = {(item.field, item.scope): item for item in semantic_frame.field_observations}
    assert observations[("occupation", "self")].normalized_value == "外贸"
    assert any("fallback_projection_refinement=candidates:" in str(note) for note in getattr(semantic_frame, "notes", []) or [])
    assert result.resolved_slots["occupation"] == "外贸"


def test_unified_understanding_keeps_ai_direct_write_fields_even_if_permission_blocks_field():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
            resolved_slots={"occupation": "在编教师"},
            confidence=0.9,
        )
    )
    ai_payload = (
        '{"primary_domain":"profile","acts":["profile_answer"],'
        '"user_questions":[],"field_observations":['
        '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self","evidence_text":"在编教师","evidence_span":"在编教师","confidence":0.98,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"partner_requirement","value":"成熟稳重，多金，身高180+","normalized_value":"成熟稳重，多金，身高180+","scope":"partner","owner":"partner","evidence_text":"成熟稳重，多金，身高180+","evidence_span":"成熟稳重，多金，身高180+","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.96}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)
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
                "在编教师",
                last_response="你现在是从事哪方面工作的呀？",
                user_profile=profile,
            ),
            force_ai=True,
        )
    )

    assert ai_service.calls == 1
    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert result.resolved_slots["partner_requirement"] == "成熟稳重，多金，身高180+"


def test_unified_understanding_uses_sync_ai_semantic_extraction_for_collection_turn_by_default():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"phone": "13526783627"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"mixed","acts":["provide_profile","provide_contact"],'
        '"user_questions":[],'
        '"field_observations":['
        '{"field":"location","value":"深圳龙华","normalized_value":"深圳龙华","scope":"self","owner":"self","evidence_text":"深圳龙华","evidence_span":"深圳龙华","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "深圳龙华，可以直接电话联系这边13526783627",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    assert ai_service.calls == 1
    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert any("ai_semantic_trigger=sync_collection_turn:contact_answer" == note for note in (result.notes or []))


def test_unified_understanding_logs_ai_semantic_summary_for_contact_scoped_ai_success(caplog):
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="contact_answer",
            subtype="contact_provided",
            resolved_slots={"wechat": "abc123456"},
            confidence=0.93,
        )
    )
    ai_payload = (
        '{"primary_domain":"mixed","acts":["provide_profile","provide_contact"],'
        '"user_questions":[],"field_observations":['
        '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self","evidence_text":"在编教师","evidence_span":"在编教师","confidence":0.97,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"wechat","value":"abc123456","normalized_value":"abc123456","scope":"contact","owner":"self","evidence_text":"abc123456","evidence_span":"abc123456","confidence":0.99,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    ai_service = _StubAIService(ai_payload)
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)
    profile = SimpleNamespace(
        last_question_state={
            "asked_fields": ["contact"],
            "side_fields": [],
            "expected_scope": "contact",
            "allow_mixed_answer": False,
        }
    )

    caplog.set_level(logging.INFO)
    result = asyncio.run(
        service.analyze(
            _make_input(
                "在编教师，微信abc123456",
                last_response="留个微信吧",
                in_contact_flow=True,
                user_profile=profile,
            ),
            force_ai=True,
        )
    )

    obs_logs = [record.message for record in caplog.records if "[unified_turn_understanding.ai_semantic_obs]" in record.message]
    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert result.resolved_slots["wechat"] == "abc123456"
    assert result.resolved_slots["occupation"] == "在编教师"
    assert any("status=success:json_frame" in message for message in obs_logs)
    assert any("pre_fields=occupation,wechat" in message for message in obs_logs)
    assert any("post_fields=occupation,wechat" in message for message in obs_logs)
    assert any("allowed=" in message and "contact" in message and "wechat" in message for message in obs_logs)


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


def test_unified_understanding_marks_occupation_short_answer_as_explicit_self_marker_in_followup_context():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="proactive_profile_provide",
            resolved_slots={"occupation": "在编教师"},
            confidence=0.91,
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
                "在编教师",
                last_response="你现在是从事哪方面的工作呀？",
                user_profile=profile,
            )
        )
    )

    persistence_plan = getattr(result, "persistence_plan", None)
    accepted = list(getattr(persistence_plan, "accepted_fields", []) or [])

    assert any(
        str(getattr(field, "field", "") or "").strip() == "occupation"
        and str(getattr(field, "acceptance_reason", "") or "").strip() == "explicit_self_marker"
        for field in accepted
    )
    assert result.resolved_slots == {"occupation": "在编教师"}


def test_unified_understanding_marks_emphatic_sex_followup_as_explicit_self_marker():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
            resolved_slots={"sex": "女"},
            confidence=0.91,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["sex"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    result = asyncio.run(
        service.analyze(
            _make_input(
                "女生啊，肯定的女的啊",
                last_response="你是男生还是女生呀？",
                user_profile=profile,
            )
        )
    )

    persistence_plan = getattr(result, "persistence_plan", None)
    accepted = list(getattr(persistence_plan, "accepted_fields", []) or [])

    assert any(
        str(getattr(field, "field", "") or "").strip() == "sex"
        and str(getattr(field, "acceptance_reason", "") or "").strip() == "explicit_self_marker"
        for field in accepted
    )
    assert result.resolved_slots == {"sex": "女"}


def test_unified_understanding_enables_sync_ai_semantic_for_high_risk_followup():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="single_slot_answer",
            resolved_slots={"occupation": "在编教师"},
            confidence=0.90,
        )
    )
    ai_service = _StubAIService(
        '{"primary_domain":"profile","acts":["profile_answer"],'
        '"user_questions":[],"field_observations":['
        '{"field":"occupation","value":"在编教师","normalized_value":"在编教师","scope":"self","owner":"self","evidence_text":"在编教师","evidence_span":"在编教师","confidence":0.98,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.97}'
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)
    profile = SimpleNamespace(
        last_question_state={
            "question_intent": "profile_followup",
            "asked_fields": ["occupation"],
            "side_fields": [],
            "expected_scope": "self",
            "allow_mixed_answer": False,
        }
    )

    env_key = "UNIFIED_TURN_SYNC_AI_HIGH_RISK_ENABLED"
    previous = os.environ.get(env_key)
    os.environ[env_key] = "1"
    try:
        result = asyncio.run(
            service.analyze(
                _make_input(
                    "在编教师",
                    last_response="你现在是从事哪方面的工作呀？",
                    user_profile=profile,
                )
            )
        )
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous

    assert ai_service.calls == 1
    assert getattr(result, "semantic_frame").source == "ai_structured_extraction"
    assert result.resolved_slots["occupation"] == "在编教师"


def test_unified_understanding_mixed_profile_answer_defaults_to_async_backfill_not_sync_ai():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"age": "28", "partner_requirement": "成熟稳重"},
            confidence=0.9,
        )
    )
    ai_service = _StubAIService(
        '{"primary_domain":"profile","acts":["profile_answer"],'
        '"user_questions":[],"field_observations":['
        '{"field":"age","value":"28","normalized_value":"28","scope":"self","owner":"self","evidence_text":"28","evidence_span":"28","confidence":0.89,"write_mode":"direct_write","source":"ai_semantic_extraction"},'
        '{"field":"partner_requirement","value":"成熟稳重","normalized_value":"成熟稳重","scope":"partner","owner":"partner","evidence_text":"成熟稳重","evidence_span":"成熟稳重","confidence":0.89,"write_mode":"direct_write","source":"ai_semantic_extraction"}'
        '],"risk_flags":[],"boundaries":[],"confidence":0.95}'
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=ai_service)
    profile = SimpleNamespace(last_question_state={})

    env_key = "UNIFIED_TURN_SYNC_AI_HIGH_RISK_ENABLED"
    previous = os.environ.get(env_key)
    os.environ[env_key] = "1"
    try:
        result = asyncio.run(
            service.analyze(
                _make_input(
                    "28岁，看重成熟稳重",
                    last_response="你也可以直接说说自己的情况和你比较看重的点。",
                    user_profile=profile,
                )
            )
        )
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous

    assert ai_service.calls == 0
    assert getattr(result, "semantic_frame").source != "ai_structured_extraction"
    assert result.resolved_slots["age"] == "28"
    assert result.resolved_slots["partner_requirement"] == "成熟稳重"


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


def test_unified_understanding_emits_structured_partner_numeric_preference_observations():
    base = TurnUnderstandingService(_StubChatService())
    semantic_result = base.analyze(_make_input("想找175以上的，30+的，月入2w+的"))
    service = UnifiedTurnUnderstandingService(_DelegatingSemanticService(semantic_result), ai_service=None)

    result = asyncio.run(service.analyze(_make_input("想找175以上的，30+的，月入2w+的")))

    observations = {
        (obs.field, str(obs.normalized_value), obs.scope): obs
        for obs in (result.semantic_frame.field_observations or [])
    }

    assert ("partner_pref_height", "身高175cm以上", "partner") in observations
    assert ("partner_pref_age", "年龄30以上", "partner") in observations
    assert ("partner_pref_income", "收入2万以上", "partner") in observations
    assert observations[("partner_pref_height", "身高175cm以上", "partner")].evidence_span
    assert observations[("partner_pref_age", "年龄30以上", "partner")].evidence_span
    assert observations[("partner_pref_income", "收入2万以上", "partner")].evidence_span


def test_unified_understanding_derives_partner_preference_subslots_from_requirement():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="profile_answer",
            subtype="multi_slot_compound",
            resolved_slots={"partner_requirement": "同医疗体系，同在深圳发展，本地优先，比自己大"},
            confidence=0.91,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(service.analyze(_make_input("同医疗体系，同在深圳发展，本地优先，比自己大")))

    assert result.resolved_slots["partner_requirement"] == "同医疗体系，同在深圳发展，本地优先，比自己大"
    assert result.resolved_slots["partner_pref_industry"] == "同医疗体系"
    assert result.resolved_slots["partner_pref_location"] == "深圳"
    assert result.resolved_slots["partner_pref_locality"] == "本地优先"
    assert result.resolved_slots["partner_pref_age_relation"] == "比自己大"
    assert result.field_derivations["partner_pref_industry"] == "同医疗体系"
    assert result.resolved_field_evidence["partner_pref_industry"].derived_from == "partner_requirement"


def test_unified_understanding_attaches_priority_decision_for_mixed_faq_turn():
    semantic_service = _DelegatingSemanticService(
        TurnUnderstandingResult(
            primary_turn_type="faq_concern",
            subtype="fee",
            resolved_slots={"occupation": "在编教师", "phone": "13526783627", "partner_requirement": "同城优先"},
            confidence=0.93,
        )
    )
    service = UnifiedTurnUnderstandingService(semantic_service, ai_service=None)

    result = asyncio.run(
        service.analyze(
            _make_input(
                "深圳在编教师，可以电话联系13526783627，怎么收费呢",
                last_response="方便简单说下自己的情况吗？",
            )
        )
    )

    assert result.priority_decision is not None
    assert result.priority_decision.primary_task == "user_question"
    assert result.priority_decision.response_mode == "answer_then_resume"
    assert "contact_record" in result.priority_decision.suppressed_tasks
