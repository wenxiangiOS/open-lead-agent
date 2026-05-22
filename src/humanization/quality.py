"""回复后的质量检查。

这个文件只报告拟人化问题、内部策略泄露等风险，
暂时不自动改写模型回复，方便后续做成可配置修复步骤。
"""

from dataclasses import dataclass, field
from typing import Any

from src.humanization.expression import ExpressionPlan
from src.policy import TurnDecision
from src.templates.config import TemplateConfig


@dataclass(frozen=True)
class ResponseQualityCheck:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": self.issues}


class ResponseQualityChecker:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def check(
        self,
        *,
        response: str,
        decision: TurnDecision,
        expression_plan: ExpressionPlan,
    ) -> ResponseQualityCheck:
        if not self.template.humanization.enabled:
            return ResponseQualityCheck(passed=True)

        issues: list[str] = []
        issues.extend(self._check_avoid_phrases(response, expression_plan))
        issues.extend(self._check_question_count(response, expression_plan))
        issues.extend(self._check_target_presence(response, decision))
        issues.extend(self._check_internal_policy_leak(response))
        return ResponseQualityCheck(passed=not issues, issues=issues)

    def _check_avoid_phrases(
        self, response: str, expression_plan: ExpressionPlan
    ) -> list[str]:
        issues = []
        for phrase in expression_plan.avoid_phrases:
            if phrase and phrase in response:
                issues.append(f"avoid_phrase:{phrase}")
        return issues

    def _check_question_count(
        self, response: str, expression_plan: ExpressionPlan
    ) -> list[str]:
        question_count = response.count("?") + response.count("？")
        if question_count > expression_plan.max_active_questions:
            return [f"too_many_questions:{question_count}"]
        return []

    def _check_target_presence(
        self, response: str, decision: TurnDecision
    ) -> list[str]:
        if decision.action not in {
            "ask_field",
            "ask_contact",
            "answer_then_ask",
            "confirm_field",
        }:
            return []
        if decision.target is None:
            return []
        target_key_terms = self._target_terms(decision)
        if any(term in response for term in target_key_terms):
            return []
        return [f"missing_target:{decision.target.key}"]

    def _target_terms(self, decision: TurnDecision) -> list[str]:
        if decision.target is None:
            return []
        terms = [
            decision.target.key,
            decision.target.label,
            *self._target_key_terms(decision.target.key),
        ]
        if decision.target.ask:
            terms.extend(self._phrase_terms(decision.target.ask))
        if getattr(decision.target, "description", ""):
            terms.extend(self._phrase_terms(decision.target.description))
        for example in getattr(decision.target, "examples", []):
            terms.extend(self._phrase_terms(example))
        return list(dict.fromkeys([term for term in terms if term]))

    def _target_key_terms(self, key: str) -> list[str]:
        aliases = {
            "sex": ["男生", "女生", "性别"],
            "age": ["年龄", "几岁", "哪年", "出生"],
            "occupation": ["工作", "职业", "做什么"],
            "location": ["城市", "哪里", "在哪"],
            "education": ["学历", "学校"],
            "phone": ["手机", "电话", "号码"],
            "wechat": ["微信"],
        }
        return aliases.get(key, [key])

    def _phrase_terms(self, text: str) -> list[str]:
        separators = ("，", "。", "？", "?", " ", "、", "：", ":", "；", ";")
        terms = [text]
        current = text
        for separator in separators:
            next_terms: list[str] = []
            for item in terms:
                next_terms.extend(part.strip() for part in item.split(separator))
            terms = next_terms
            current = current.replace(separator, " ")
        terms.extend(part for part in current.split() if len(part) >= 2)
        return [term for term in terms if len(term) >= 2]

    def _check_internal_policy_leak(self, response: str) -> list[str]:
        leaked_terms = (
            "TurnDecision",
            "expression_plan",
            "字段路由",
            "内部策略",
            "contact_gate",
            "field_routing",
            "debug",
        )
        return [f"internal_leak:{term}" for term in leaked_terms if term in response]
