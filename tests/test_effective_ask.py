import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class EmptyUnderstandingLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if "single turn understanding layer" in system_prompt:
            return "{}"
        return "好的"


class SequenceProfileUnderstandingLLM:
    configured = True

    def __init__(self, field_turns: list[dict[str, object]]):
        self.field_turns = field_turns
        self.index = 0

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if "single turn understanding layer" not in system_prompt:
            return "好的"
        fields = self.field_turns[self.index] if self.index < len(self.field_turns) else {}
        self.index += 1
        return json.dumps(
            {
                "intents": ["profile"],
                "observations": [
                    {"field": key, "value": value, "confidence": 0.95}
                    for key, value in fields.items()
                ],
            },
            ensure_ascii=False,
        )


def test_faq_interruption_does_not_consume_previous_field_ask(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    engine = ConversationEngine(get_active_template(), store, EmptyUnderstandingLLM())

    first = asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="ask-faq-user")))
    assert first.next_field is not None
    assert first.next_field["key"] == "sex"

    second = asyncio.run(
        engine.chat(ChatRequest(question="你们怎么收费？", accountId="ask-faq-user"))
    )

    assert store.get_ask_counts("ask-faq-user").get("sex", 0) == 0
    assert second.next_field is not None
    assert second.next_field["key"] == "sex"


def test_non_response_consumes_previous_field_ask(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    engine = ConversationEngine(get_active_template(), store, EmptyUnderstandingLLM())

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="ask-short-user")))
    second = asyncio.run(engine.chat(ChatRequest(question="嗯", accountId="ask-short-user")))

    assert store.get_ask_counts("ask-short-user")["sex"] == 1
    assert second.next_field is not None
    assert second.next_field["key"] == "sex"


def test_refusal_consumes_previous_field_ask_and_skips_field(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    engine = ConversationEngine(get_active_template(), store, EmptyUnderstandingLLM())

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="ask-refusal-user")))
    second = asyncio.run(
        engine.chat(ChatRequest(question="不方便说", accountId="ask-refusal-user"))
    )

    assert store.get_ask_counts("ask-refusal-user")["sex"] == 1
    assert "sex" in store.get_skipped_fields("ask-refusal-user")
    assert second.next_field is not None
    assert second.next_field["key"] != "sex"


def test_answering_field_collects_without_consuming_ask_limit(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    engine = ConversationEngine(
        get_active_template(),
        store,
        SequenceProfileUnderstandingLLM([{}, {"sex": "男"}]),
    )

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="ask-answer-user")))
    second = asyncio.run(engine.chat(ChatRequest(question="男", accountId="ask-answer-user")))

    assert second.collected == {"sex": "男"}
    assert store.get_ask_counts("ask-answer-user").get("sex", 0) == 0
