import asyncio
import json

from src.conversation import ChatRequest, ConversationEngine
from src.extraction import ExtractionEngine
from src.storage import MemoryStore
from src.templates.config import TemplateConfig, get_active_template, reset_template_cache


class ExtractionLLM:
    configured = True

    def __init__(self, extraction_response: dict):
        self.extraction_response = extraction_response
        self.system_prompts: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.system_prompts.append(system_prompt)
        if "Extract lead profile fields" in system_prompt:
            return json.dumps(self.extraction_response, ensure_ascii=False)
        return "好的"


class CountingLLM:
    configured = True

    def __init__(self):
        self.calls: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls.append(system_prompt)
        return "你好，请问有什么可以帮你？"


def _pure_support_template() -> TemplateConfig:
    return TemplateConfig(
        template={
            "id": "support",
            "name": "智能客服",
            "description": "不收集资料，只回答用户问题。",
        },
        agent={
            "name": "小助理",
            "language": "zh-CN",
            "role": "智能客服",
            "tone": "友好、专业、简洁。",
            "welcome_message": "你好，请问有什么可以帮你？",
        },
        fields=[],
        contact={"enabled": False, "methods": []},
    )


def test_matchmaking_extraction_uses_configured_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    llm = ExtractionLLM({"sex": "男", "age": 30, "education": "本科", "location": "深圳"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("男的，30岁，本科，在深圳", {}))

    assert extracted == {"sex": "男", "age": 30, "education": "本科", "location": "深圳"}
    assert "key=sex" in llm.system_prompts[0]
    assert "key=student_grade" not in llm.system_prompts[0]
    assert "Template-specific extraction instructions:" in llm.system_prompts[0]
    assert "用户本轮消息：" in llm.system_prompts[0]
    assert "男的，30岁，本科，在深圳" in llm.system_prompts[0]
    assert "{user_message}" not in llm.system_prompts[0]
    assert "{configured_fields}" not in llm.system_prompts[0]


def test_low_tier_fields_are_extractable_by_default(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    llm = ExtractionLLM({"height": "178cm", "weight": "70kg"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("我178cm，70kg", {}))

    assert extracted == {"height": "178cm", "weight": "70kg"}
    assert "key=height" in llm.system_prompts[0]
    assert "key=weight" in llm.system_prompts[0]


def test_extract_false_fields_are_not_sent_or_accepted(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template().model_copy(deep=True)
    for field in template.fields:
        if field.key == "height":
            field.extract = False
    llm = ExtractionLLM({"height": "178cm", "weight": "70kg"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("我178cm，70kg", {}))

    assert extracted == {"weight": "70kg"}
    assert "key=height" not in llm.system_prompts[0]
    assert "key=weight" in llm.system_prompts[0]


def test_extract_false_contact_methods_are_not_sent_or_accepted(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template().model_copy(deep=True)
    for method in template.contact.methods:
        if method.key == "wechat":
            method.extract = False
    llm = ExtractionLLM({"phone": "17688987654", "wechat": "wx-user"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("手机号17688987654，微信wx-user", {}))

    assert extracted == {"phone": "17688987654"}
    assert "key=phone" in llm.system_prompts[0]
    assert "key=wechat" not in llm.system_prompts[0]


def test_education_extraction_uses_education_template_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    template = get_active_template()
    llm = ExtractionLLM({"student_grade": "初二", "subject": "数学"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("孩子初二，想补数学", {}))

    assert extracted == {"student_grade": "初二", "subject": "数学"}
    assert "key=student_grade" in llm.system_prompts[0]
    assert "key=sex" not in llm.system_prompts[0]


def test_extraction_filters_unknown_fields_and_existing_profile(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    llm = ExtractionLLM(
        {
            "sex": "女",
            "age": 31,
            "password": "secret",
            "education": "",
            "marital_status": "未知",
        }
    )
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("女，31岁", {"sex": "男"}))

    assert extracted == {"age": 31}


def test_extraction_normalizes_common_number_and_enum_phrasing(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    llm = ExtractionLLM({"sex": "男的", "age": "30岁"})
    engine = ExtractionEngine(template, llm)

    extracted = asyncio.run(engine.extract("男的，30岁", {}))

    assert extracted == {"sex": "男", "age": 30}


def test_conversation_merges_extracted_fields_before_choosing_next_field(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = ExtractionLLM({"sex": "男", "age": 30})
    engine = ConversationEngine(get_active_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="男的，30岁", accountId="extract-user"))
    )

    assert response.collected == {"sex": "男", "age": 30}
    assert response.next_field is not None
    assert response.next_field["key"] == "education"


def test_no_configured_fields_skips_extraction_call():
    llm = CountingLLM()
    engine = ExtractionEngine(_pure_support_template(), llm)

    extracted = asyncio.run(engine.extract("你们怎么收费？", {}))

    assert extracted == {}
    assert llm.calls == []


def test_no_configured_fields_chat_does_not_collect_or_ask_next_field():
    llm = CountingLLM()
    engine = ConversationEngine(_pure_support_template(), MemoryStore(), llm)

    response = asyncio.run(
        engine.chat(ChatRequest(question="你们怎么收费？", accountId="support-user"))
    )

    assert response.collected == {}
    assert response.next_field is None
    assert response.response == "你好，请问有什么可以帮你？"
    assert len(llm.calls) == 1
    assert "Next field to collect" not in llm.calls[0]
