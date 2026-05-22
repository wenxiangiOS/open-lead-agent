"""配置驱动的合规规则，用于停止推进或结束对话。Compliance rules."""

from typing import Any

from src.templates.config import ComplianceRuleConfig, TemplateConfig
from src.understanding import TurnSemanticFrame


class ComplianceDecision:
    def __init__(self, rule: ComplianceRuleConfig):
        self.rule = rule

    @property
    def message(self) -> str:
        return self.rule.message

    @property
    def reason(self) -> str:
        return f"compliance:{self.rule.id}"


class CompliancePolicy:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def evaluate(
        self,
        profile: dict[str, Any],
        semantic_frame: TurnSemanticFrame | None = None,
    ) -> ComplianceDecision | None:
        if not self.template.compliance.enabled:
            return None
        for rule in self.template.compliance.rules:
            if self._matches(rule, profile, semantic_frame):
                return ComplianceDecision(rule)
        return None

    def _matches(
        self,
        rule: ComplianceRuleConfig,
        profile: dict[str, Any],
        semantic_frame: TurnSemanticFrame | None,
    ) -> bool:
        if self._matches_field_condition(rule, profile):
            return True
        return self._matches_semantic_signal(rule, semantic_frame)

    def _matches_field_condition(
        self,
        rule: ComplianceRuleConfig,
        profile: dict[str, Any],
    ) -> bool:
        condition = rule.when
        if not condition.field:
            return False
        value = profile.get(condition.field)
        if value in (None, ""):
            return False

        operator = condition.operator
        if operator in {"equals", "eq", "=="}:
            return str(value) == str(condition.value)
        if operator in {"not_equals", "ne", "!="}:
            return str(value) != str(condition.value)
        if operator == "contains":
            return str(condition.value) in str(value)
        if operator == "in":
            return value in condition.in_values or str(value) in {
                str(item) for item in condition.in_values
            }
        if operator in {"lt", "lte", "gt", "gte"}:
            return self._compare_number(value, condition.value, operator)
        return False

    def _matches_semantic_signal(
        self,
        rule: ComplianceRuleConfig,
        semantic_frame: TurnSemanticFrame | None,
    ) -> bool:
        if semantic_frame is None or not rule.semantic_signals:
            return False
        if semantic_frame.confidence < rule.semantic_min_confidence:
            return False
        configured_signals = {signal.strip().lower() for signal in rule.semantic_signals}
        frame_signals = {signal.strip().lower() for signal in semantic_frame.compliance_signals}
        return bool(configured_signals & frame_signals)

    def _compare_number(self, left: Any, right: Any, operator: str) -> bool:
        left_number = self._to_number(left)
        right_number = self._to_number(right)
        if left_number is None or right_number is None:
            return False
        if operator == "lt":
            return left_number < right_number
        if operator == "lte":
            return left_number <= right_number
        if operator == "gt":
            return left_number > right_number
        return left_number >= right_number

    def _to_number(self, value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        digits = "".join(char for char in str(value) if char.isdigit() or char == ".")
        if not digits:
            return None
        try:
            return float(digits)
        except ValueError:
            return None
