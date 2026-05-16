import asyncio

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class RecordingLLM:
    configured = True

    def __init__(self):
        self.system_prompt = ""

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.system_prompt = system_prompt
        return "好的"


def test_system_prompt_includes_template_reply_language(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    asyncio.run(engine.chat(ChatRequest(question="你好", accountId="prompt-language-user")))

    assert "Reply language: zh-CN." in llm.system_prompt
    assert "Always respond in the configured reply language" in llm.system_prompt
