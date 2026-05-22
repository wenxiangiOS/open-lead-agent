import asyncio

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class StableLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        return "好的"


def test_matchmaking_closes_after_contact_collected_when_contact_gate_is_ready(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(get_active_template(), MemoryStore(), StableLLM())

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="我的电话是17688987654",
                accountId="close-after-contact-user",
                profile={
                    "sex": "男",
                    "age": 30,
                    "education": "本科",
                    "occupation": "IT",
                    "location": "深圳",
                    "phone": "17688987654",
                },
            )
        )
    )

    assert response.next_field is None
    assert "后续如果有合适进展" in response.response


def test_early_contact_does_not_close_before_required_profile_is_ready(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(get_active_template(), MemoryStore(), StableLLM())

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="我的电话是17688987654",
                accountId="early-contact-user",
                profile={"phone": "17688987654"},
            )
        )
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "sex"
    assert "后续如果有合适进展" not in response.response
