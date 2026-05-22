import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class SequenceUnderstandingLLM:
    configured = True

    def __init__(self, payloads: list[dict]):
        self.payloads = payloads
        self.calls: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls.append(system_prompt)
        if "single turn understanding layer" in system_prompt:
            if self.payloads:
                return json.dumps(self.payloads.pop(0), ensure_ascii=False)
            return "{}"
        return "好的"


def test_conflicting_field_creates_confirmation_then_accepts_new_value(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    store.update_profile("pending-user", {"sex": "男", "age": 29})
    llm = SequenceUnderstandingLLM(
        [
            {"observations": [{"field": "age", "value": "30岁"}]},
            {},
        ]
    )
    engine = ConversationEngine(get_active_template(), store, llm, debug_prompt=True)

    first = asyncio.run(
        engine.chat(ChatRequest(question="我30岁", accountId="pending-user"))
    )

    assert first.next_field is not None
    assert first.next_field["key"] == "age"
    assert "之前是29" in first.response
    assert "改成30" in first.response
    assert store.get_profile("pending-user")["age"] == 29
    assert store.get_pending_confirmation("pending-user") is not None
    assert first.debug_decision is not None
    assert first.debug_decision["action"] == "confirm_field"

    second = asyncio.run(
        engine.chat(ChatRequest(question="对，改成30", accountId="pending-user"))
    )

    assert second.collected == {"age": 30}
    assert store.get_profile("pending-user")["age"] == 30
    assert store.get_pending_confirmation("pending-user") is None
    assert second.next_field is not None
    assert second.next_field["key"] == "education"


def test_low_confidence_pending_can_be_rejected(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    store.update_profile("reject-pending-user", {"sex": "男"})
    llm = SequenceUnderstandingLLM(
        [
            {
                "observations": [
                    {
                        "field": "age",
                        "value": "90后",
                        "confidence": 0.4,
                        "write_mode": "soft_confirm",
                    }
                ]
            },
            {},
        ]
    )
    engine = ConversationEngine(get_active_template(), store, llm)

    first = asyncio.run(
        engine.chat(ChatRequest(question="90后", accountId="reject-pending-user"))
    )

    assert first.next_field is not None
    assert first.next_field["key"] == "age"
    assert "90后" in first.response
    assert "age" not in store.get_profile("reject-pending-user")
    assert store.get_pending_confirmation("reject-pending-user") is not None

    second = asyncio.run(
        engine.chat(ChatRequest(question="不是", accountId="reject-pending-user"))
    )

    assert "age" not in store.get_profile("reject-pending-user")
    assert store.get_pending_confirmation("reject-pending-user") is None
    assert second.next_field is not None
    assert second.next_field["key"] == "age"


def test_multiple_pending_confirmations_are_processed_as_queue(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    store.update_profile("pending-queue-user", {"sex": "男", "age": 29, "education": "大专"})
    llm = SequenceUnderstandingLLM(
        [
            {
                "observations": [
                    {"field": "age", "value": "30岁"},
                    {"field": "education", "value": "本科"},
                ]
            },
            {},
            {},
        ]
    )
    engine = ConversationEngine(get_active_template(), store, llm)

    first = asyncio.run(
        engine.chat(ChatRequest(question="我30岁，本科", accountId="pending-queue-user"))
    )

    assert first.next_field is not None
    assert first.next_field["key"] == "age"
    assert len(store.get_pending_confirmations("pending-queue-user")) == 2

    second = asyncio.run(
        engine.chat(ChatRequest(question="对", accountId="pending-queue-user"))
    )

    assert store.get_profile("pending-queue-user")["age"] == 30
    assert second.next_field is not None
    assert second.next_field["key"] == "education"
    assert len(store.get_pending_confirmations("pending-queue-user")) == 1

    third = asyncio.run(
        engine.chat(ChatRequest(question="对", accountId="pending-queue-user"))
    )

    assert store.get_profile("pending-queue-user")["education"] == "本科"
    assert store.get_pending_confirmation("pending-queue-user") is None
    assert third.next_field is not None
