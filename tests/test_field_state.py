import asyncio

from src.collection.state import FieldStateService
from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class StableLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        return "好的"


def test_field_state_marks_asked_limit_as_covered(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    service = FieldStateService(template)

    states = service.build_states(
        profile={"sex": "男", "age": 30, "education": "本科", "occupation": "IT"},
        ask_counts={"location": 2},
    )

    assert states["location"].status == "covered"
    assert states["location"].covered is True


def test_skipped_field_is_not_reasked(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    store = MemoryStore()
    engine = ConversationEngine(get_active_template(), store, StableLLM())

    first = asyncio.run(
        engine.chat(
            ChatRequest(
                question="孩子初二",
                accountId="skip-field-user",
                profile={"student_grade": "初二"},
            )
        )
    )
    assert first.next_field is not None
    assert first.next_field["key"] == "subject"

    second = asyncio.run(
        engine.chat(
            ChatRequest(
                question="这个不方便说",
                accountId="skip-field-user",
            )
        )
    )

    assert "subject" in store.get_skipped_fields("skip-field-user")
    assert second.next_field is not None
    assert second.next_field["key"] != "subject"
