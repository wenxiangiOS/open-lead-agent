import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class OffTargetLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if "single turn understanding layer" in system_prompt:
            return "{}"
        return "你平时喜欢什么颜色呀？"


class ResponseTimeoutLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if "single turn understanding layer" in system_prompt:
            return "{}"
        raise TimeoutError("Request timed out.")


def test_response_timeout_falls_back_to_target_ask(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(get_active_template(), MemoryStore(), ResponseTimeoutLLM())

    response = asyncio.run(
        engine.chat(ChatRequest(question="我想找对象", accountId="response-timeout-user"))
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "sex"
    assert response.response == "我先了解下，你这边是男生还是女生呀？"


def test_off_target_field_question_is_repaired(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(
        get_active_template(),
        MemoryStore(),
        OffTargetLLM(),
        debug_prompt=True,
    )

    response = asyncio.run(
        engine.chat(ChatRequest(question="我想找对象", accountId="off-target-user"))
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "sex"
    assert response.response == "我先了解下，你这边是男生还是女生呀？"
    assert response.debug_quality_check is not None
    assert response.debug_quality_check["passed"] is True


def test_target_consistency_repair_can_be_disabled(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template().model_copy(deep=True)
    template.humanization.enforce_target_consistency = False
    engine = ConversationEngine(template, MemoryStore(), OffTargetLLM(), debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="我想找对象", accountId="off-target-disabled-user"))
    )

    assert response.response == "你平时喜欢什么颜色呀？"
    assert response.debug_quality_check is not None
    assert response.debug_quality_check["passed"] is False
    assert "missing_target:sex" in response.debug_quality_check["issues"]


class AnswerThenAskLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if "single turn understanding layer" in system_prompt:
            return json.dumps({"intents": ["profile"], "observations": []}, ensure_ascii=False)
        return "好的"


def test_answer_then_ask_uses_configured_target_ask(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = ConversationEngine(get_active_template(), MemoryStore(), AnswerThenAskLLM())

    response = asyncio.run(
        engine.chat(ChatRequest(question="怎么收费？", accountId="faq-consistency-user"))
    )

    assert response.response.startswith("基础咨询通常可以免费")
    assert "我先了解下，你这边是男生还是女生呀？" in response.response
