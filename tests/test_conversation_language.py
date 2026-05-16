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


def test_system_prompt_includes_configured_persona(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    asyncio.run(engine.chat(ChatRequest(question="你好", accountId="prompt-persona-user")))

    assert "Role: 婚恋咨询顾问." in llm.system_prompt
    assert "Persona:" in llm.system_prompt
    assert "你是小缘，以真实自然的口吻和用户聊天" in llm.system_prompt
    assert "Goals:" in llm.system_prompt
    assert "Behavior rules:" in llm.system_prompt
    assert "像真人聊天，不机械不死板" in llm.system_prompt
    assert "Boundaries:" in llm.system_prompt
    assert "不要虚构固定年龄、从业年限、所在城市或个人履历" in llm.system_prompt


def test_system_prompt_includes_dialogue_policy(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    asyncio.run(engine.chat(ChatRequest(question="你好", accountId="prompt-policy-user")))

    assert "Turn goal:" in llm.system_prompt
    assert "自然聊天中推进资料收集" in llm.system_prompt
    assert "Dialogue priorities:" in llm.system_prompt
    assert "离异/分居合规与结束流程" in llm.system_prompt
    assert "General principles:" in llm.system_prompt
    assert "低优字段（身高/体重/姓名）只被动记录" in llm.system_prompt
    assert "婚况与分居处理:" in llm.system_prompt
    assert "拟人化表达:" in llm.system_prompt
    assert "生成方式:" in llm.system_prompt
    assert "承接优先:" in llm.system_prompt
    assert "禁止事项:" in llm.system_prompt
    assert "Dialogue examples:" in llm.system_prompt
    assert "User: 你们靠谱吗" in llm.system_prompt
