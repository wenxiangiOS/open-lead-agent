import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class SemanticLLM:
    configured = True

    def __init__(self, understanding_payload: dict, reply: str = "好的"):
        self.understanding_payload = understanding_payload
        self.reply = reply
        self.prompts: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.prompts.append(system_prompt)
        if "single turn understanding layer" in system_prompt:
            return json.dumps(self.understanding_payload, ensure_ascii=False)
        return self.reply


def test_semantic_faq_intent_answers_even_without_keyword(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM({"intents": ["faq"], "faq_intent": "pricing"})
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="这个怎么算？", accountId="semantic-faq-user"))
    )

    assert response.response.startswith("基础咨询通常可以免费")
    assert response.next_field is not None
    assert response.next_field["key"] == "sex"


def test_semantic_conversation_end_stops_collection(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM(
        {
            "intents": ["conversation_end"],
            "reply_act": "stop",
        }
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="算了，不聊了", accountId="semantic-stop-user"))
    )

    assert response.next_field is None
    assert response.response == get_active_template().conversation.stop_message


def test_semantic_contact_intent_asks_contact_when_gate_is_ready(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM(
        {
            "intents": ["contact_intent"],
            "reply_act": "continue",
        }
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)
    store = engine.store
    for field_key in ("marital_status", "partner_requirement", "monthly_income"):
        store.increment_ask_count("semantic-contact-user", field_key)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="可以留联系方式",
                accountId="semantic-contact-user",
                profile={
                    "sex": "男",
                    "age": 30,
                    "education": "本科",
                    "occupation": "IT",
                    "location": "深圳",
                },
            )
        )
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "phone"


def test_semantic_compliance_signal_can_end_conversation(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM(
        {
            "intents": ["profile"],
            "compliance_signals": ["underage"],
            "confidence": 0.9,
        }
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="我还没成年", accountId="semantic-underage-user"))
    )

    assert response.next_field is None
    assert "只面向成年人" in response.response
    assert response.debug_decision is not None
    assert response.debug_decision["reason"] == "compliance:underage"


def test_semantic_compliance_signal_respects_confidence(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM(
        {
            "intents": ["profile"],
            "compliance_signals": ["underage"],
            "confidence": 0.4,
        }
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="我看起来挺年轻", accountId="semantic-low-risk-user"))
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "sex"
    assert "只面向成年人" not in response.response


def test_unknown_semantic_compliance_signal_is_ignored(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = SemanticLLM(
        {
            "intents": ["profile"],
            "compliance_signals": ["unknown_policy_signal"],
            "confidence": 0.99,
        }
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="普通咨询", accountId="semantic-unknown-signal-user"))
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "sex"
