from __future__ import annotations

from types import SimpleNamespace

from src.services.core.chat_service import ChatService


def test_extract_turn_level_fields_does_not_fallback_to_raw_rules_when_understanding_exists():
    host = SimpleNamespace(
        _effective_resolved_slots=lambda _u: {},
        turn_understanding_service=SimpleNamespace(
            _extract_deterministic_profile_fields=lambda _m: (_ for _ in ()).throw(RuntimeError("should_not_call")),
            _apply_extraction_guards=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should_not_call")),
        ),
    )
    understanding = SimpleNamespace(
        resolved_slots={"occupation": "怎么多了"},
        field_derivations={},
        persistence_plan=SimpleNamespace(accepted_fields=[]),
    )

    extracted = ChatService._extract_turn_level_fields(
        host,
        "找对象 女生找男朋友 暂时就 怎么多了",
        understanding_result=understanding,
        last_response="",
    )

    assert extracted == {}


def test_extract_turn_level_fields_keeps_legacy_fallback_only_when_understanding_missing():
    host = SimpleNamespace(
        _effective_resolved_slots=lambda _u: {},
        turn_understanding_service=SimpleNamespace(
            _extract_deterministic_profile_fields=lambda _m: {"location": "深圳"},
            _apply_extraction_guards=lambda fields, *_args, **_kwargs: dict(fields),
        ),
    )

    extracted = ChatService._extract_turn_level_fields(
        host,
        "我在深圳",
        understanding_result=None,
        last_response="",
    )

    assert extracted == {"location": "深圳"}
