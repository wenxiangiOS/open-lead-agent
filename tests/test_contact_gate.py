from src.collection.state import FieldStateService
from src.policy.contact_gate import ContactGate
from src.templates.config import get_active_template, reset_template_cache


def test_matchmaking_contact_gate_requires_core_and_medium_coverage(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    gate = ContactGate(template)
    states = FieldStateService(template).build_states(
        profile={
            "sex": "女",
            "age": 28,
            "education": "本科",
            "occupation": "教师",
            "location": "深圳",
        },
        ask_counts={},
    )

    assert gate.allows_contact(
        {
            "sex": "女",
            "age": 28,
            "education": "本科",
            "occupation": "教师",
            "location": "深圳",
        },
        {},
        states,
    ) is False


def test_matchmaking_contact_gate_allows_after_medium_ask_limits(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    profile = {
        "sex": "女",
        "age": 28,
        "education": "本科",
        "occupation": "教师",
        "location": "深圳",
    }
    ask_counts = {
        "marital_status": 1,
        "partner_requirement": 1,
        "monthly_income": 1,
    }
    states = FieldStateService(template).build_states(profile=profile, ask_counts=ask_counts)
    gate = ContactGate(template)

    assert gate.allows_contact(profile, ask_counts, states) is True
    explanation = gate.explain(profile, ask_counts, states)
    assert explanation["optional_uncovered"] == []
    assert explanation["optional_covered"] == [
        "marital_status",
        "partner_requirement",
        "monthly_income",
    ]
