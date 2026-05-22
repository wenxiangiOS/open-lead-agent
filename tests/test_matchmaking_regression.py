import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.storage import MemoryStore
from src.templates.config import get_active_template, reset_template_cache


class ScriptedLLM:
    configured = True

    def __init__(self, understanding_payloads: list[dict], reply: str = "好的"):
        self.understanding_payloads = understanding_payloads
        self.reply = reply
        self.prompts: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.prompts.append(system_prompt)
        if "single turn understanding layer" in system_prompt:
            if self.understanding_payloads:
                return json.dumps(self.understanding_payloads.pop(0), ensure_ascii=False)
            return "{}"
        return self.reply


def test_dense_profile_plus_faq_goes_to_contact_after_core_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = ScriptedLLM(
        [
            {
                "intents": ["profile", "faq"],
                "faq_intent": "pricing",
                "observations": [
                    {"field": "sex", "value": "男"},
                    {"field": "age", "value": "30岁"},
                    {"field": "education", "value": "本科"},
                    {"field": "occupation", "value": "运营"},
                    {"field": "location", "value": "深圳"},
                    {"field": "partner_requirement", "value": "稳定点的女生"},
                ],
            }
        ]
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="男，30岁，本科，在深圳做运营，想找稳定点的女生，怎么收费？",
                accountId="dense-faq-user",
            )
        )
    )

    assert response.collected == {
        "sex": "男",
        "age": 30,
        "education": "本科",
        "occupation": "运营",
        "location": "深圳",
        "partner_requirement": "稳定点的女生",
    }
    assert response.response.startswith("基础咨询通常可以免费")
    assert response.next_field is not None
    assert response.next_field["key"] == "monthly_income"
    assert "月收入" in response.response


def test_phone_and_wechat_same_number_are_both_collected_and_close(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    store = MemoryStore()
    store.update_profile(
        "same-contact-user",
        {
            "sex": "男",
            "age": 30,
            "education": "本科",
            "occupation": "IT",
            "location": "深圳",
        },
    )
    llm = ScriptedLLM(
        [
            {
                "intents": ["contact_intent"],
                "observations": [
                    {"field": "phone", "value": "17688987654"},
                    {"field": "wechat", "value": "17688987654"},
                ],
            }
        ]
    )
    engine = ConversationEngine(get_active_template(), store, llm)

    response = asyncio.run(
        engine.chat(
            ChatRequest(question="电话和微信同号，17688987654", accountId="same-contact-user")
        )
    )

    profile = store.get_profile("same-contact-user")
    assert profile["phone"] == "17688987654"
    assert profile["wechat"] == "17688987654"
    assert response.collected == {"phone": "17688987654", "wechat": "17688987654"}
    assert response.next_field is None
    assert "后续如果有合适进展" in response.response


def test_short_answer_binding_context_is_sent_to_understanding(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = ScriptedLLM(
        [
            {},
            {"observations": [{"field": "sex", "value": "男"}]},
        ]
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    first = asyncio.run(
        engine.chat(ChatRequest(question="我想找对象", accountId="short-binding-user"))
    )
    second = asyncio.run(
        engine.chat(ChatRequest(question="男", accountId="short-binding-user"))
    )

    assert first.next_field is not None
    assert first.next_field["key"] == "sex"
    assert second.collected == {"sex": "男"}
    second_understanding_prompt = llm.prompts[2]
    assert "previous assistant turn was collecting key=sex" in second_understanding_prompt
    assert "Previous assistant question:" in second_understanding_prompt


def test_simple_greeting_after_opening_pauses_before_field_collection(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = ScriptedLLM([{"intents": ["greeting"], "reply_act": "continue"}])
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="你好", accountId="opening-greeting-user"))
    )

    assert response.next_field is None
    assert response.response == "你好呀，你也可以先简单介绍下自己，我先了解下你的情况。"
    assert response.debug_decision is not None
    assert response.debug_decision["reason"] == "opening:greeting_pause"


def test_pending_divorce_semantic_signal_ends_conversation(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = ScriptedLLM(
        [
            {
                "intents": ["profile"],
                "compliance_signals": ["pending_divorce"],
                "confidence": 0.92,
                "observations": [
                    {"field": "marital_status", "value": "手续办理中"},
                ],
            }
        ]
    )
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="我现在离婚手续还在办", accountId="pending-divorce-user"))
    )

    assert response.next_field is None
    assert "手续都处理清楚" in response.response
    assert response.debug_decision is not None
    assert response.debug_decision["reason"] == "compliance:pending_divorce"
