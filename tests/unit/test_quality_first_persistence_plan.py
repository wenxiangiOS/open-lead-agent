from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from src.models.user_profile import UserProfile
from src.modules.conversation_understanding.domain.field_acceptance_service import FieldAcceptanceService
from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    FieldObservation,
    TurnPersistencePlan,
    TurnSemanticFrame,
)
from src.services.core.chat_service import ChatService
from src.services.core.chat_service_collection_extraction_service import ChatServiceCollectionExtractionService
from src.services.core.chat_service_generation_service import ChatServiceGenerationService


def _obs(
    *,
    field: str,
    value,
    confidence: float,
    source: str,
    scope: str = "self",
    write_mode: str = "direct_write",
    evidence_text: str | None = None,
):
    return FieldObservation(
        field=field,
        value=value,
        normalized_value=value,
        scope=scope,
        owner="self" if scope in {"self", "contact"} else scope,
        evidence_text=str(evidence_text if evidence_text is not None else value),
        evidence_span=str(value),
        confidence=confidence,
        write_mode=write_mode,
        source=source,
    )


def test_high_risk_fallback_observation_is_staged_as_provisional():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[_obs(field="occupation", value="在编教师", confidence=0.99, source="semantic_deterministic")],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert not accepted
    assert len(provisional) == 1
    assert provisional[0].field == "occupation"
    assert provisional[0].persistence_state == "provisional"
    assert provisional[0].source_channel in {"hybrid", "fallback"}
    assert not pending
    assert not rejected


def test_high_risk_ai_observation_can_be_committed():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="ai_structured_extraction",
        primary_domain="profile",
        field_observations=[_obs(field="occupation", value="在编教师", confidence=0.95, source="ai_semantic_extraction")],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "occupation"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].source_channel == "ai"
    assert not provisional
    assert not pending
    assert not rejected


def test_ai_direct_write_commits_even_when_confidence_below_old_high_risk_threshold():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="ai_structured_extraction",
        primary_domain="profile",
        field_observations=[_obs(field="occupation", value="在编教师", confidence=0.84, source="ai_semantic_extraction")],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "occupation"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].source_channel == "ai"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_marker_sex_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="sex",
                value="女",
                confidence=0.98,
                source="semantic_explicit_self_marker",
                evidence_text="深圳龙华在编女教师",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "sex"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_marker_occupation_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="occupation",
                value="在编教师",
                confidence=0.98,
                source="semantic_explicit_self_marker",
                evidence_text="深圳龙华在编教师",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "occupation"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_marker_age_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="age",
                value=36,
                confidence=0.98,
                source="semantic_explicit_self_marker",
                evidence_text="90后啊",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "age"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_marker_age_with_birth_year_suffix_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="age",
                value=28,
                confidence=0.98,
                source="semantic_explicit_self_marker",
                evidence_text="98的，单身",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "age"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_income_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="monthly_income",
                value="一年18左右",
                confidence=0.98,
                source="semantic_deterministic",
                evidence_text="我自己收入不高一年18左右",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "monthly_income"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_self_marker_income_short_answer_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="monthly_income",
                value="20k+",
                confidence=0.98,
                source="semantic_explicit_self_marker",
                evidence_text="20K+",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "monthly_income"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_self_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_explicit_partner_requirement_can_be_committed_without_ai():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="partner_requirement",
                value="成熟稳重，多金，身高180+",
                confidence=0.96,
                source="semantic_deterministic",
                scope="partner",
                evidence_text="喜欢成熟稳重，多金，身高180+",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert len(accepted) == 1
    assert accepted[0].field == "partner_requirement"
    assert accepted[0].persistence_state == "committed"
    assert accepted[0].acceptance_reason == "explicit_partner_marker"
    assert accepted[0].source_channel == "hybrid"
    assert not provisional
    assert not pending
    assert not rejected


def test_non_explicit_hybrid_sex_stays_provisional():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[
            _obs(
                field="sex",
                value="女",
                confidence=0.98,
                source="semantic_deterministic",
                evidence_text="找男朋友",
            )
        ],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert not accepted
    assert len(provisional) == 1
    assert provisional[0].field == "sex"
    assert provisional[0].acceptance_reason == "high_risk_non_ai_guard"
    assert not pending
    assert not rejected


def test_non_ai_core_low_confidence_goes_to_pending_confirm():
    service = FieldAcceptanceService()
    frame = TurnSemanticFrame(
        version="v1",
        source="hybrid_semantic_projection",
        primary_domain="profile",
        field_observations=[_obs(field="education", value="本科", confidence=0.70, source="semantic_deterministic")],
    )

    accepted, provisional, pending, rejected = service.accept(frame=frame)

    assert not accepted
    assert not provisional
    assert len(pending) == 1
    assert pending[0].field == "education"
    assert pending[0].persistence_state == "pending_confirm"
    assert not rejected


def test_merge_uses_only_committed_fields_and_keeps_high_risk_ai_guard():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="在编教师",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            ),
            AcceptedField(
                field="age",
                value=28,
                normalized_value=28,
                scope="self",
                evidence_text="28",
                confidence=0.88,
                acceptance_reason="stage",
                update_action="stage_as_provisional",
                persistence_state="provisional",
                source_channel="fallback",
            ),
        ],
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"occupation": "在编教师"}
    assert "occupation" in merged_meta
    assert "age" not in merged_data


def test_merge_blocks_on_profile_version_mismatch():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="education",
                value="本科",
                normalized_value="本科",
                scope="self",
                evidence_text="本科",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ],
        expected_profile_updated_at="2026-04-12T12:00:00",
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={"location": "深圳"},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 1)),
    )

    assert merged_data == {"location": "深圳"}
    assert "__persistence_plan_guard__" in merged_meta


def test_merge_blocks_on_profile_version_mismatch_using_profile_version():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="education",
                value="本科",
                normalized_value="本科",
                scope="self",
                evidence_text="本科",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ],
        expected_profile_version=7,
        expected_profile_updated_at="2026-04-12T12:00:00",
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={"location": "深圳"},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(profile_version=8, updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"location": "深圳"}
    assert "__persistence_plan_guard__" in merged_meta
    assert merged_meta["__persistence_plan_guard__"]["reason"] == "profile_version_mismatch"


def test_merge_allows_when_profile_version_matches_even_if_updated_at_differs():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="education",
                value="本科",
                normalized_value="本科",
                scope="self",
                evidence_text="本科",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ],
        expected_profile_version=12,
        expected_profile_updated_at="2026-04-12T12:00:00",
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(profile_version=12, updated_at=datetime(2026, 4, 12, 12, 0, 30)),
    )

    assert merged_data == {"education": "本科"}
    assert "__persistence_plan_guard__" not in merged_meta


def test_merge_drops_high_risk_fields_not_committed_by_persistence_plan():
    plan = TurnPersistencePlan(accepted_fields=[])
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={"occupation": "怎么多了", "location": "深圳"},
        extraction_meta={"occupation": {"source": "response_extract"}, "location": {"source": "response_extract"}},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert "occupation" not in merged_data
    assert merged_data["location"] == "深圳"
    assert "occupation" not in merged_meta


def test_generation_merge_skips_unpersisted_plan_fields():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="在编教师",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ]
    )
    understanding = SimpleNamespace(persistence_plan=plan)
    profile = UserProfile(account_id="u_test_generation_merge_skip")

    merged = ChatServiceGenerationService._merge_persistence_plan_into_collection_result(
        collection_result={"collected": False, "all_fields": []},
        understanding_result=understanding,
        user_profile=profile,
    )

    assert merged["all_fields"] == []
    assert merged["collected"] is False


def test_generation_merge_keeps_persisted_plan_fields():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="在编教师",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ]
    )
    understanding = SimpleNamespace(persistence_plan=plan)
    profile = UserProfile(account_id="u_test_generation_merge_ok")
    profile.occupation = "在编教师"
    profile.collection_progress["occupation"] = True

    merged = ChatServiceGenerationService._merge_persistence_plan_into_collection_result(
        collection_result={"all_fields": []},
        understanding_result=understanding,
        user_profile=profile,
    )

    assert merged["all_fields"] == [{"field": "occupation", "value": "在编教师", "source": "persistence_plan"}]
    assert merged["collected"] is True


def test_merge_allows_explicit_self_marker_sex_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="sex",
                value="女",
                normalized_value="女",
                scope="self",
                evidence_text="深圳龙华在编女教师",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"sex": "女"}
    assert merged_meta["sex"]["source"] == "persistence_plan_acceptance"


def test_merge_allows_explicit_self_marker_occupation_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="深圳龙华在编教师",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"occupation": "在编教师"}
    assert merged_meta["occupation"]["source"] == "persistence_plan_acceptance"


def test_merge_allows_explicit_self_marker_monthly_income_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="monthly_income",
                value="一年18左右",
                normalized_value="一年18左右",
                scope="self",
                evidence_text="我自己收入不高一年18左右",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"monthly_income": "一年18左右"}
    assert merged_meta["monthly_income"]["source"] == "persistence_plan_acceptance"


def test_merge_allows_explicit_self_marker_age_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="age",
                value=28,
                normalized_value=28,
                scope="self",
                evidence_text="98年的",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"age": 28}
    assert merged_meta["age"]["source"] == "persistence_plan_acceptance"


def test_merge_keeps_rule_age_when_meta_is_explicit_self_marker():
    plan = TurnPersistencePlan(accepted_fields=[])
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={"age": "28", "age_label": "98年"},
        extraction_meta={
            "age": {
                "source": "semantic_explicit_self_marker",
                "confidence": 0.92,
                "source_text": "98年的，喜欢成熟稳重，多金，身高180+",
            },
            "age_label": {
                "source": "rule",
                "confidence": 0.88,
                "source_text": "98年的，喜欢成熟稳重，多金，身高180+",
            },
        },
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data["age"] == "28"
    assert merged_data["age_label"] == "98年"
    assert merged_meta["age"]["source"] == "semantic_explicit_self_marker"


def test_merge_allows_explicit_partner_marker_partner_requirement_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="partner_requirement",
                value="成熟稳重，多金，身高180+",
                normalized_value="成熟稳重，多金，身高180+",
                scope="partner",
                evidence_text="喜欢成熟稳重，多金，身高180+",
                confidence=0.96,
                acceptance_reason="explicit_partner_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding_result = SimpleNamespace(persistence_plan=plan)

    merged_data, merged_meta = ChatServiceCollectionExtractionService._merge_persistence_plan_accepted_fields(
        extracted_data={},
        extraction_meta={},
        understanding_result=understanding_result,
        user_profile=SimpleNamespace(updated_at=datetime(2026, 4, 12, 12, 0, 0)),
    )

    assert merged_data == {"partner_requirement": "成熟稳重，多金，身高180+"}
    assert merged_meta["partner_requirement"]["source"] == "persistence_plan_acceptance"


def test_generation_merge_allows_explicit_self_marker_age_from_persistence_plan():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="age",
                value=28,
                normalized_value=28,
                scope="self",
                evidence_text="98年的",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding = SimpleNamespace(persistence_plan=plan)
    profile = UserProfile(account_id="u_generation_merge_age_marker")
    profile.age = 28
    profile.collection_progress["age"] = True

    merged = ChatServiceGenerationService._merge_persistence_plan_into_collection_result(
        collection_result={"all_fields": []},
        understanding_result=understanding,
        user_profile=profile,
    )

    assert merged["all_fields"] == [{"field": "age", "value": 28, "source": "persistence_plan"}]
    assert merged["collected"] is True


def test_chat_service_effective_resolved_slots_uses_committed_plan_fields_only():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="location",
                value="深圳",
                normalized_value="深圳",
                scope="self",
                evidence_text="深圳",
                confidence=0.95,
                acceptance_reason="direct_write",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="ai",
            )
        ],
        provisional_fields=[
            AcceptedField(
                field="occupation",
                value="怎么多了",
                normalized_value="怎么多了",
                scope="self",
                evidence_text="怎么多了",
                confidence=0.55,
                acceptance_reason="stage",
                update_action="stage_as_provisional",
                persistence_state="provisional",
                source_channel="fallback",
            )
        ],
    )
    understanding = SimpleNamespace(
        resolved_slots={"occupation": "怎么多了", "location": "深圳"},
        persistence_plan=plan,
    )

    slots = ChatService._effective_resolved_slots(understanding)  # noqa: SLF001

    assert slots == {"location": "深圳"}
    assert "occupation" not in slots


def test_chat_service_effective_resolved_slots_keeps_explicit_self_marker_sex():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="sex",
                value="女",
                normalized_value="女",
                scope="self",
                evidence_text="深圳龙华在编女教师",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding = SimpleNamespace(
        resolved_slots={},
        persistence_plan=plan,
    )

    slots = ChatService._effective_resolved_slots(understanding)  # noqa: SLF001

    assert slots == {"sex": "女"}


def test_chat_service_effective_resolved_slots_keeps_explicit_self_marker_occupation():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="occupation",
                value="在编教师",
                normalized_value="在编教师",
                scope="self",
                evidence_text="深圳龙华在编教师",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding = SimpleNamespace(
        resolved_slots={},
        persistence_plan=plan,
    )

    slots = ChatService._effective_resolved_slots(understanding)  # noqa: SLF001

    assert slots == {"occupation": "在编教师"}


def test_chat_service_effective_resolved_slots_keeps_explicit_self_marker_monthly_income():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="monthly_income",
                value="一年18左右",
                normalized_value="一年18左右",
                scope="self",
                evidence_text="我自己收入不高一年18左右",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding = SimpleNamespace(
        resolved_slots={},
        persistence_plan=plan,
    )

    slots = ChatService._effective_resolved_slots(understanding)  # noqa: SLF001

    assert slots == {"monthly_income": "一年18左右"}


def test_chat_service_effective_resolved_slots_keeps_explicit_self_marker_age():
    plan = TurnPersistencePlan(
        accepted_fields=[
            AcceptedField(
                field="age",
                value=28,
                normalized_value=28,
                scope="self",
                evidence_text="98年的",
                confidence=0.98,
                acceptance_reason="explicit_self_marker",
                update_action="accept_as_new",
                persistence_state="committed",
                source_channel="hybrid",
            )
        ]
    )
    understanding = SimpleNamespace(
        resolved_slots={},
        persistence_plan=plan,
    )

    slots = ChatService._effective_resolved_slots(understanding)  # noqa: SLF001

    assert slots == {"age": 28}
