from src.policy.field_routing import FieldRoutingPolicy
from src.templates.config import get_active_template, reset_template_cache


def test_core_main_field_can_carry_related_medium_side_target(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    policy = FieldRoutingPolicy(get_active_template())

    plan = policy.plan(
        profile={"sex": "男", "age": 30, "education": "本科"},
        ask_counts={},
    )

    assert plan.main is not None
    assert plan.main.key == "occupation"
    assert plan.side is not None
    assert plan.side.key == "monthly_income"
    assert plan.reason == "core_main_with_optional_side"


def test_context_anchor_prefers_related_missing_core_before_medium(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    policy = FieldRoutingPolicy(get_active_template())

    plan = policy.plan(
        profile={"sex": "男", "location": "深圳"},
        ask_counts={},
        collected_this_turn={"location": "深圳"},
    )

    assert plan.main is not None
    assert plan.main.key == "occupation"
    assert plan.side is None
    assert plan.reason == "contextual_core_followup"


def test_context_anchor_can_choose_related_medium_when_no_related_core(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    policy = FieldRoutingPolicy(get_active_template())

    plan = policy.plan(
        profile={
            "sex": "男",
            "age": 30,
            "education": "本科",
            "occupation": "程序员",
            "location": "深圳",
        },
        ask_counts={},
        collected_this_turn={"occupation": "程序员"},
    )

    assert plan.main is not None
    assert plan.main.key == "monthly_income"
    assert plan.side is None
    assert plan.reason == "contextual_medium_followup"
