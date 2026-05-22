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

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="prompt-language-user")))

    assert "Reply language: zh-CN." in llm.system_prompt
    assert "Always respond in the configured reply language" in llm.system_prompt


def test_system_prompt_includes_configured_persona(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="prompt-persona-user")))

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

    asyncio.run(engine.chat(ChatRequest(question="我想找对象", accountId="prompt-policy-user")))

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


def test_debug_prompt_is_hidden_by_default(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="你好", accountId="prompt-hidden-user"))
    )

    assert response.debug_system_prompt is None


def test_debug_prompt_can_be_returned(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="你好", accountId="prompt-visible-user"))
    )

    assert response.debug_system_prompt is not None
    assert "Dialogue examples:" in response.debug_system_prompt
    assert response.debug_expression_plan is not None
    assert response.debug_expression_plan["max_active_questions"] == 1
    assert response.debug_quality_check is not None
    assert "passed" in response.debug_quality_check


def test_debug_response_includes_faq_match(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(ChatRequest(question="How much is the tuition?", accountId="faq-debug-user"))
    )

    assert response.debug_faq_match is not None
    assert response.debug_faq_match["intent"] == "pricing"
    assert response.debug_faq_match["matched_keyword"] == "tuition"
    assert response.debug_knowledge_context is not None
    assert response.debug_knowledge_context["faq_match"]["intent"] == "pricing"
    assert response.debug_knowledge_context["rag_result_count"] == 0
    assert response.debug_decision is not None
    assert response.debug_decision["reason"] == "faq:pricing"


def test_system_prompt_marks_pending_field_answers_as_collected(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    store = MemoryStore()
    store.update_profile(
        "prompt-collected-user",
        {
            "sex": "男",
            "age": 30,
            "education": "本科",
            "occupation": "IT",
            "location": "深圳",
            "phone": "17688987654",
        },
    )
    engine = ConversationEngine(get_active_template(), store, llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="wxwefiwef",
                accountId="prompt-collected-user",
                profile={"wechat": "wxwefiwef"},
            )
        )
    )

    assert response.debug_system_prompt is not None
    assert "Current turn collected values:" in response.debug_system_prompt
    assert '"wechat": "wxwefiwef"' in response.debug_system_prompt
    assert "do not say you did not understand" in response.debug_system_prompt
    assert response.next_field is None
    assert "后续如果有合适进展" in response.response


def test_field_routing_uses_contextual_followup(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="男生，在深圳",
                accountId="natural-routing-user",
                profile={"sex": "男", "location": "深圳"},
            )
        )
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "occupation"
    assert "natural_followup" in llm.system_prompt
    assert "不要像表单跳问" in llm.system_prompt
    assert "Humanized expression plan:" in llm.system_prompt
    assert "用户本轮刚提供了：性别, 所在城市" in llm.system_prompt
    assert '"target_key": "occupation"' in llm.system_prompt
    assert "never reveal" in llm.system_prompt


def test_core_field_prompt_can_include_related_medium_side_target(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    store = MemoryStore()
    store.update_profile(
        "side-target-user",
        {"sex": "男", "age": 30, "education": "本科"},
    )
    engine = ConversationEngine(get_active_template(), store, llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="你好",
                accountId="side-target-user",
            )
        )
    )

    assert response.next_field is not None
    assert response.next_field["key"] == "occupation"
    assert response.debug_decision is not None
    assert response.debug_decision["side_target"] == "monthly_income"
    assert "Optional related side field: monthly_income" in llm.system_prompt
    assert '"side_target_key": "monthly_income"' in llm.system_prompt


def test_compliance_rule_can_end_conversation(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = RecordingLLM()
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm, debug_prompt=True)

    response = asyncio.run(
        engine.chat(
            ChatRequest(
                question="我16岁",
                accountId="underage-user",
                profile={"age": 16},
            )
        )
    )

    assert response.next_field is None
    assert "只面向成年人" in response.response
    assert response.debug_decision is not None
    assert response.debug_decision["reason"] == "compliance:underage"
