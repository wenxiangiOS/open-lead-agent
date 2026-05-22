"""生成单轮拟人化表达计划。

这个文件只描述“如何承接用户、如何自然问下一步”，
不直接生成或改写最终回复文本。
"""

from dataclasses import dataclass, field
from typing import Any

from src.policy import TurnDecision
from src.templates.config import TemplateConfig


@dataclass(frozen=True)
class ExpressionPlan:
    action: str
    acknowledge_required: bool
    acknowledge_focus: str = ""
    target_key: str | None = None
    target_label: str | None = None
    side_target_key: str | None = None
    side_target_label: str | None = None
    guidance: str = ""
    avoid_phrases: list[str] = field(default_factory=list)
    max_active_questions: int = 1

    def public_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "acknowledge_required": self.acknowledge_required,
            "acknowledge_focus": self.acknowledge_focus,
            "target_key": self.target_key,
            "target_label": self.target_label,
            "side_target_key": self.side_target_key,
            "side_target_label": self.side_target_label,
            "guidance": self.guidance,
            "avoid_phrases": self.avoid_phrases,
            "max_active_questions": self.max_active_questions,
        }


class ExpressionPlanner:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def build(
        self,
        *,
        decision: TurnDecision,
        user_message: str,
        collected_this_turn: dict[str, Any],
        recent_history: list[dict[str, str]],
    ) -> ExpressionPlan:
        if not self.template.humanization.enabled:
            return ExpressionPlan(
                action=decision.action,
                acknowledge_required=False,
                target_key=decision.target_key,
                target_label=self._target_label(decision),
                side_target_key=self._side_target_key(decision),
                side_target_label=self._side_target_label(decision),
                guidance=decision.expression_hint,
            )

        return ExpressionPlan(
            action=decision.action,
            acknowledge_required=self._acknowledge_required(decision, collected_this_turn),
            acknowledge_focus=self._acknowledge_focus(
                decision=decision,
                user_message=user_message,
                collected_this_turn=collected_this_turn,
            ),
            target_key=decision.target_key,
            target_label=self._target_label(decision),
            side_target_key=self._side_target_key(decision),
            side_target_label=self._side_target_label(decision),
            guidance=self._guidance(decision),
            avoid_phrases=self._avoid_phrases(recent_history),
            max_active_questions=self._max_active_questions(decision),
        )

    def _acknowledge_required(
        self, decision: TurnDecision, collected_this_turn: dict[str, Any]
    ) -> bool:
        if decision.action in {"end", "close", "answer_only", "answer_then_ask"}:
            return True
        return bool(collected_this_turn)

    def _acknowledge_focus(
        self,
        *,
        decision: TurnDecision,
        user_message: str,
        collected_this_turn: dict[str, Any],
    ) -> str:
        if decision.action in {"end", "close"}:
            return "本轮需要自然说明边界或收尾，不要继续推进新问题。"
        if decision.action in {"answer_only", "answer_then_ask"}:
            return "用户本轮在提问或表达顾虑，先接住问题重点。"
        if collected_this_turn:
            labels = self._field_labels(collected_this_turn)
            return f"用户本轮刚提供了：{', '.join(labels)}。"
        if user_message.strip():
            return "用户刚发来消息，先用一句自然短承接再推进。"
        return ""

    def _guidance(self, decision: TurnDecision) -> str:
        base = decision.expression_hint
        if decision.target is not None:
            text = (
                f"{base} 本轮最多主动问一个问题，围绕 "
                f"{decision.target.key}（{decision.target.label}）推进。"
            )
            if decision.side_target is not None:
                text += (
                    f" {decision.side_target.key}（{decision.side_target.label}）只能作为"
                    "顺手补充，不要写成第二个并列盘问。"
                )
            return text.strip()
        return base

    def _avoid_phrases(self, recent_history: list[dict[str, str]]) -> list[str]:
        phrases = [
            "收到",
            "好的，已记录",
            "请提供",
            "方便说下",
            "我再确认一下",
            "为了更好地",
        ]
        if self.template.humanization.avoid_repeated_openings:
            phrases.extend(self._recent_assistant_openings(recent_history))
        return list(dict.fromkeys([phrase for phrase in phrases if phrase]))

    def _recent_assistant_openings(self, recent_history: list[dict[str, str]]) -> list[str]:
        window = self.template.humanization.recent_phrase_window
        openings: list[str] = []
        for item in recent_history[-window:]:
            if item.get("role") != "assistant":
                continue
            content = item.get("content", "").strip()
            if not content:
                continue
            first_sentence = self._first_sentence(content)
            if first_sentence:
                openings.append(first_sentence)
        return openings

    def _first_sentence(self, content: str) -> str:
        for separator in ("。", "？", "！", "\n"):
            if separator in content:
                return content.split(separator, 1)[0].strip()
        return content[:18].strip()

    def _max_active_questions(self, decision: TurnDecision) -> int:
        configured = self.template.humanization.max_active_questions_per_turn
        if decision.side_target is not None:
            return max(configured, 2)
        return configured

    def _field_labels(self, collected_this_turn: dict[str, Any]) -> list[str]:
        field_map = {field.key: field.label for field in self.template.fields}
        field_map.update({method.key: method.label for method in self.template.contact.methods})
        return [field_map.get(key, key) for key in collected_this_turn]

    def _target_label(self, decision: TurnDecision) -> str | None:
        if decision.target is None:
            return None
        return decision.target.label

    def _side_target_key(self, decision: TurnDecision) -> str | None:
        if decision.side_target is None:
            return None
        return decision.side_target.key

    def _side_target_label(self, decision: TurnDecision) -> str | None:
        if decision.side_target is None:
            return None
        return decision.side_target.label
