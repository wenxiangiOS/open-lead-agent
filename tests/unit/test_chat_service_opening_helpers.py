from types import SimpleNamespace

import pytest

from src.services.core.chat_service import ChatService, OpeningIntentSignal


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), object())


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

