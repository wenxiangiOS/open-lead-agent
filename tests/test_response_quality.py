from src.humanization import ExpressionPlan, ResponseQualityChecker
from src.policy import TurnDecision
from src.templates.config import get_active_template, reset_template_cache


def test_response_quality_detects_robotic_or_leaky_reply(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    checker = ResponseQualityChecker(template)
    target = next(field for field in template.fields if field.key == "occupation")
    decision = TurnDecision(action="ask_field", reason="natural_followup", target=target)
    expression_plan = ExpressionPlan(
        action="ask_field",
        acknowledge_required=True,
        target_key="occupation",
        target_label="职业",
        avoid_phrases=["收到"],
        max_active_questions=1,
    )

    result = checker.check(
        response="收到。请提供字段路由里的信息，你今年多大？现在做什么？",
        decision=decision,
        expression_plan=expression_plan,
    )

    assert result.passed is False
    assert "avoid_phrase:收到" in result.issues
    assert "too_many_questions:2" in result.issues
    assert "internal_leak:字段路由" in result.issues


def test_response_quality_passes_natural_targeted_reply(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()
    checker = ResponseQualityChecker(template)
    target = next(field for field in template.fields if field.key == "occupation")
    decision = TurnDecision(action="ask_field", reason="natural_followup", target=target)
    expression_plan = ExpressionPlan(
        action="ask_field",
        acknowledge_required=True,
        target_key="occupation",
        target_label="职业",
        avoid_phrases=["收到"],
        max_active_questions=1,
    )

    result = checker.check(
        response="深圳这边选择挺多的，你现在主要做什么工作呀？",
        decision=decision,
        expression_plan=expression_plan,
    )

    assert result.passed is True
    assert result.issues == []
