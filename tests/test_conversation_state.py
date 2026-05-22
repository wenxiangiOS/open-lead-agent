import asyncio

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class StableLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        return "好的"


def test_dialog_id_isolates_conversation_state(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(get_active_template(), MemoryStore(), StableLLM())

    first_dialog = asyncio.run(
        engine.chat(
            ChatRequest(
                question="我是男的",
                accountId="same-user",
                dialogId="dialog-a",
                profile={"sex": "男"},
            )
        )
    )
    second_dialog = asyncio.run(
        engine.chat(
            ChatRequest(
                question="我想找对象",
                accountId="same-user",
                dialogId="dialog-b",
            )
        )
    )

    assert first_dialog.next_field is not None
    assert first_dialog.next_field["key"] == "age"
    assert second_dialog.next_field is not None
    assert second_dialog.next_field["key"] == "sex"
