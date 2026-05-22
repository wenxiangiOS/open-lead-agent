import asyncio
import json

from src.templates.config import (
    ContactMethodConfig,
    FieldPermissionRuleConfig,
    get_active_template,
    reset_template_cache,
)
from src.understanding import TurnUnderstandingEngine


class UnderstandingLLM:
    configured = True

    def __init__(self, payload: dict):
        self.payload = payload
        self.prompts: list[str] = []

    async def generate(self, system_prompt: str, user_message: str) -> str:
        self.prompts.append(system_prompt)
        return json.dumps(self.payload, ensure_ascii=False)


class TimeoutUnderstandingLLM:
    configured = True

    async def generate(self, system_prompt: str, user_message: str) -> str:
        raise TimeoutError("Request timed out.")


def test_understanding_timeout_returns_empty_fallback(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = TurnUnderstandingEngine(get_active_template(), TimeoutUnderstandingLLM())

    result = asyncio.run(engine.analyze("男的", {}, expected_field="sex"))

    assert result.accepted_fields == {}
    assert result.semantic_frame.confidence == 0.0


def test_understanding_accepts_structured_observations(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "intents": ["profile", "faq"],
            "observations": [
                {"field": "location", "value": "深圳", "scope": "self"},
                {"field": "occupation", "value": "运营", "scope": "self"},
            ],
            "faq_intent": "pricing",
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("我在深圳，做运营，怎么收费？", {}))

    assert result.semantic_frame.intents == ["profile", "faq"]
    assert result.semantic_frame.faq_intent == "pricing"
    assert result.semantic_frame.turn_mode == "default"
    assert result.persistence_plan.accepted_fields == {
        "location": "深圳",
        "occupation": "运营",
    }
    assert result.persistence_plan.rejected_fields == {}
    assert "Preferred JSON shape" in llm.prompts[0]
    assert "scope=self" in llm.prompts[0]
    assert "dense introduction" in llm.prompts[0]


def test_dense_intro_marks_observed_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "intents": ["profile", "faq"],
            "faq_intent": "pricing",
            "observations": [
                {"field": "sex", "value": "男"},
                {"field": "age", "value": "30岁"},
                {"field": "location", "value": "深圳"},
                {"field": "occupation", "value": "运营"},
            ],
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(
        engine.analyze("男，30岁，在深圳做运营，想先问下怎么收费", {})
    )

    assert result.semantic_frame.turn_mode == "dense_intro"
    assert result.semantic_frame.no_reask_fields == ["age", "location", "occupation", "sex"]
    assert result.persistence_plan.accepted_fields == {
        "sex": "男",
        "age": 30,
        "location": "深圳",
        "occupation": "运营",
    }


def test_understanding_rejects_unknown_and_existing_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {"field": "age", "value": "30岁"},
                {"field": "password", "value": "secret"},
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("30岁", {"age": 29}))

    assert result.persistence_plan.accepted_fields == {}
    assert result.persistence_plan.pending_fields == {"age": {"current": 29, "new": 30}}
    assert result.persistence_plan.rejected_fields == {"password": "secret"}


def test_understanding_low_confidence_goes_pending(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {
                    "field": "age",
                    "value": "90后",
                    "confidence": 0.4,
                    "write_mode": "soft_confirm",
                }
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("90后", {}))

    assert result.persistence_plan.accepted_fields == {}
    assert result.persistence_plan.pending_fields == {"age": "90后"}


def test_normal_risk_low_confidence_goes_provisional(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {
                    "field": "last_name",
                    "value": "陈",
                    "confidence": 0.45,
                    "write_mode": "direct_write",
                }
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("姓陈", {}))

    assert result.persistence_plan.accepted_fields == {}
    assert result.persistence_plan.provisional_fields == {"last_name": "陈"}
    assert result.persistence_plan.pending_fields == {}
    assert (
        result.persistence_plan.observation_log[0].reason
        == "low_confidence_stage_as_provisional"
    )


def test_high_risk_untrusted_source_requires_confirmation(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {
                    "field": "monthly_income",
                    "value": "2万-5万",
                    "confidence": 0.95,
                    "write_mode": "direct_write",
                    "source": "regex",
                }
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("2万-5万", {}))

    assert result.persistence_plan.accepted_fields == {}
    assert result.persistence_plan.pending_fields == {"monthly_income": "2万-5万"}
    assert result.persistence_plan.observation_log[0].reason == "high_risk_untrusted_source"


def test_understanding_rejects_invalid_contact_method(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {"field": "phone", "value": "123"},
                {"field": "wechat", "value": "wx_user_01"},
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("电话123，微信wx_user_01", {}))

    assert result.persistence_plan.accepted_fields == {"wechat": "wx_user_01"}
    assert result.persistence_plan.rejected_fields == {"phone": "123"}


def test_understanding_supports_configured_email_and_telegram(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template().model_copy(deep=True)
    template.contact.methods.extend(
        [
            ContactMethodConfig(key="email", label="邮箱", type="email"),
            ContactMethodConfig(key="telegram", label="Telegram", type="telegram"),
        ]
    )
    llm = UnderstandingLLM(
        {
            "observations": [
                {"field": "email", "value": "USER@Example.COM"},
                {"field": "telegram", "value": "open_lead"},
            ]
        }
    )
    engine = TurnUnderstandingEngine(template, llm)

    result = asyncio.run(engine.analyze("邮箱USER@Example.COM，telegram open_lead", {}))

    assert result.persistence_plan.accepted_fields == {
        "email": "user@example.com",
        "telegram": "@open_lead",
    }


def test_faq_only_turn_blocks_hallucinated_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "intents": ["faq"],
            "faq_intent": "pricing",
            "observations": [
                {"field": "age", "value": "30岁", "scope": "self"},
            ],
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("怎么收费？", {}))

    assert result.persistence_plan.accepted_fields == {}
    assert result.persistence_plan.rejected_fields == {"age": "30岁"}
    assert result.persistence_plan.observation_log[0].reason == "faq_turn_blocks_field_write"


def test_contact_context_blocks_profile_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "intents": ["contact_intent"],
            "reply_act": "contact_answer",
            "observations": [
                {"field": "phone", "value": "13800138000", "scope": "contact"},
                {"field": "age", "value": "13800138000", "scope": "self"},
            ],
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(
        engine.analyze(
            "13800138000",
            {},
            expected_field="phone",
            last_question="留个手机号可以吗？",
        )
    )

    assert result.persistence_plan.accepted_fields == {"phone": "13800138000"}
    assert result.persistence_plan.rejected_fields == {"age": "13800138000"}


def test_short_answer_binds_to_expected_field(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "intents": ["profile"],
            "observations": [
                {"field": "age", "value": "30岁", "scope": "self"},
                {"field": "monthly_income", "value": "30岁", "scope": "self"},
            ],
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("30", {}, expected_field="age"))

    assert result.persistence_plan.accepted_fields == {"age": 30}
    assert result.persistence_plan.rejected_fields == {"monthly_income": "30岁"}


def test_passive_height_weight_preserve_user_units(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    llm = UnderstandingLLM(
        {
            "observations": [
                {"field": "height", "value": "168+"},
                {"field": "weight", "value": "50kg"},
            ]
        }
    )
    engine = TurnUnderstandingEngine(get_active_template(), llm)

    result = asyncio.run(engine.analyze("身高168+，体重50kg", {}))

    assert result.persistence_plan.accepted_fields == {
        "height": "168+",
        "weight": "50kg",
    }


def test_template_field_permission_rule_blocks_industry_specific_slots(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template().model_copy(deep=True)
    template.field_permissions.rules.append(
        FieldPermissionRuleConfig(
            name="partner_preference_scope",
            intents=["partner_preference"],
            allow_fields=["partner_requirement"],
            allow_mixed_answer=False,
            reason="partner_preference_only",
        )
    )
    llm = UnderstandingLLM(
        {
            "intents": ["partner_preference"],
            "observations": [
                {"field": "education", "value": "本科", "scope": "self"},
                {"field": "partner_requirement", "value": "本科", "scope": "partner"},
            ],
        }
    )
    engine = TurnUnderstandingEngine(template, llm)

    result = asyncio.run(engine.analyze("想找本科的", {}))

    assert result.persistence_plan.accepted_fields == {"partner_requirement": "本科"}
    assert result.persistence_plan.rejected_fields == {"education": "本科"}
