"""单轮动作决策策略。

这个文件负责决定本轮该做什么：答疑、合规结束、
询问资料字段、询问联系方式，或自然收尾。
"""

from dataclasses import dataclass
from typing import Any

from src.collection.confirmation import PendingConfirmation
from src.collection.state import FieldState
from src.contact import ContactEngine
from src.faq import FAQMatch
from src.policy.closing import ClosingPolicy
from src.policy.compliance import CompliancePolicy
from src.policy.contact_gate import ContactGate
from src.policy.field_routing import FieldRoutingPolicy
from src.policy.opening import OpeningPolicy
from src.policy.turn_priority import TurnPriorityPolicy
from src.templates.config import ContactMethodConfig, FieldConfig, TemplateConfig
from src.understanding import TurnSemanticFrame


@dataclass
class TurnDecision:
    action: str
    reason: str
    target: FieldConfig | ContactMethodConfig | None = None
    side_target: FieldConfig | None = None
    response: str = ""
    expression_hint: str = ""

    @property
    def target_key(self) -> str | None:
        if self.target is None:
            return None
        return self.target.key

    def public_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "target": self.target_key,
            "side_target": self.side_target.key if self.side_target else None,
            "expression_hint": self.expression_hint,
        }


class TurnPolicy:
    def __init__(self, template: TemplateConfig):
        self.template = template
        self.compliance = CompliancePolicy(template)
        self.closing = ClosingPolicy(template)
        self.field_routing = FieldRoutingPolicy(template)
        self.contact_gate = ContactGate(template)
        self.contact = ContactEngine(template)
        self.opening = OpeningPolicy(template)
        self.turn_priority = TurnPriorityPolicy()

    def decide(
        self,
        *,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        collected_this_turn: dict[str, Any],
        field_states: dict[str, FieldState] | None = None,
        faq_match: FAQMatch | None,
        semantic_frame: TurnSemanticFrame | None = None,
        pending_confirmation: PendingConfirmation | None = None,
        user_message: str = "",
        recent_history: list[dict[str, str]] | None = None,
    ) -> TurnDecision:
        compliance = self.compliance.evaluate(profile, semantic_frame)
        if compliance is not None:
            return TurnDecision(
                action="end",
                reason=compliance.reason,
                response=compliance.message,
                expression_hint="命中合规结束规则，本轮不要继续收集资料或联系方式。",
            )

        opening = self.opening.evaluate(
            user_message=user_message,
            profile=profile,
            collected_this_turn=collected_this_turn,
            recent_history=recent_history or [],
            semantic_frame=semantic_frame,
        )
        if opening is not None and faq_match is None and pending_confirmation is None:
            return TurnDecision(
                action="answer_only",
                reason=opening.reason,
                response=opening.message,
                expression_hint="用户刚回应开场问候，本轮先低压接住，不立刻进入字段采集。",
            )

        contact_allowed = self.contact_gate.allows_contact(profile, ask_counts, field_states)
        early_closing = self.closing.evaluate(
            profile=profile,
            field_states=field_states,
            collected_this_turn=collected_this_turn,
            contact_allowed=contact_allowed,
        )

        field_plan = self.field_routing.plan(
            profile,
            ask_counts,
            collected_this_turn,
            field_states,
        )
        next_field = field_plan.main
        side_field = field_plan.side
        contact_method = None
        if contact_allowed:
            contact_method = self.contact.next_contact_method(profile, ask_counts)
            if contact_method is not None and (
                next_field is None or not getattr(next_field, "required", False)
            ):
                next_field = None
                side_field = None

        priority = self.turn_priority.decide(
            semantic_frame=semantic_frame,
            faq_match=faq_match,
            pending_confirmation=pending_confirmation,
            next_field=next_field,
            contact_method=contact_method,
            early_closing_ready=early_closing is not None,
        )

        if priority.task == "conversation_end":
            return TurnDecision(
                action="close",
                reason=priority.reason,
                response=self.template.conversation.stop_message,
                expression_hint="用户本轮表达不想继续，本轮礼貌停下，不再追问资料或联系方式。",
            )

        if priority.task == "pending_confirmation" and pending_confirmation is not None:
            target = self._item_by_key(pending_confirmation.field_key)
            if target is not None:
                return TurnDecision(
                    action="confirm_field",
                    reason=f"pending_confirmation:{pending_confirmation.reason}",
                    target=target,
                    response=self._confirmation_message(pending_confirmation, target),
                    expression_hint=(
                        "本轮优先确认之前悬而未决的字段，不要继续推进新的资料字段。"
                    ),
                )

        if priority.task == "answer_question":
            if faq_match is None:
                return TurnDecision(
                    action="answer_only",
                    reason=priority.reason,
                    expression_hint="用户本轮在提问或表达顾虑，先回应这个重点，不推进资料收集。",
                )
            if early_closing is not None:
                return TurnDecision(
                    action="close",
                    reason=f"faq:{faq_match.intent}_then_close",
                    response=self._join_responses(faq_match.answer, early_closing.message),
                    expression_hint="用户本轮有问题或顾虑，先答清楚，再自然收尾。",
                )
            can_continue = faq_match.continue_collection and (
                next_field is not None or contact_method is not None
            )
            if can_continue:
                target = next_field or contact_method
                return TurnDecision(
                    action="answer_then_ask",
                    reason=f"faq:{faq_match.intent}",
                    target=target,
                    side_target=side_field if target == next_field else None,
                    response=faq_match.answer,
                    expression_hint="用户本轮在提问，先把问题答清楚，再轻轻回到下一步。",
                )
            return TurnDecision(
                action="answer_only",
                reason=f"faq:{faq_match.intent}",
                response=faq_match.answer,
                expression_hint="用户本轮在提问，只答疑，不推进资料收集。",
            )

        if priority.task == "contact_capture" and contact_method is not None:
            return TurnDecision(
                action="ask_contact",
                reason=priority.reason,
                target=contact_method,
                expression_hint="用户本轮主动提到联系方式，顺着进入联系方式，不再回头追普通资料。",
            )

        if priority.task == "closing" and early_closing is not None:
            return TurnDecision(
                action="close",
                reason=early_closing.reason,
                response=early_closing.message,
                expression_hint="联系方式流程已经满足收尾条件，本轮自然收尾，不再追问普通资料。",
            )

        if priority.task == "profile_collection" and next_field is not None:
            return TurnDecision(
                action="ask_field",
                reason=self._field_reason(next_field, collected_this_turn, field_plan.reason),
                target=next_field,
                side_target=side_field,
                expression_hint=self._field_expression_hint(
                    next_field,
                    collected_this_turn,
                    side_field,
                    field_plan.reason,
                ),
            )

        closing = self.closing.evaluate(
            profile=profile,
            field_states=field_states,
            collected_this_turn=collected_this_turn,
            contact_allowed=contact_allowed,
            no_next_action=True,
        )
        if closing is not None:
            return TurnDecision(
                action="close",
                reason=closing.reason,
                response=closing.message,
                expression_hint="没有下一步可推进，简短自然收尾。",
            )

        return TurnDecision(action="answer_only", reason="no_next_action")

    def _field_reason(
        self,
        next_field: FieldConfig,
        collected_this_turn: dict[str, Any],
        routing_reason: str = "",
    ) -> str:
        if routing_reason.startswith("contextual_"):
            return f"natural_followup:{routing_reason}"
        if routing_reason:
            return routing_reason
        if not collected_this_turn:
            return "field_missing"
        return "natural_followup"

    def _field_expression_hint(
        self,
        next_field: FieldConfig,
        collected_this_turn: dict[str, Any],
        side_field: FieldConfig | None = None,
        routing_reason: str = "",
    ) -> str:
        side_hint = ""
        if side_field is not None:
            side_hint = (
                f" 可以把中等字段 {side_field.key}（{side_field.label}）作为轻量顺带信息，"
                "但不能让它抢主线；如果句子不自然，就只问主字段。"
            )
        if not collected_this_turn:
            return (
                f"本轮自然推进核心字段 {next_field.key}（{next_field.label}）。"
                f"{side_hint}"
            )
        collected_keys = ", ".join(collected_this_turn.keys())
        if routing_reason == "contextual_medium_followup":
            return (
                f"用户本轮刚提供了 {collected_keys}，当前没有更相近的未收集核心字段，"
                f"可以顺着追问中等字段 {next_field.key}（{next_field.label}）。"
            )
        return (
            f"用户本轮刚提供了 {collected_keys}，可以顺着这个信息自然追问 "
            f"核心字段 {next_field.key}（{next_field.label}），不要像表单跳问。"
            f"{side_hint}"
        )

    def _item_by_key(self, key: str) -> FieldConfig | ContactMethodConfig | None:
        for field in self.template.fields:
            if field.key == key:
                return field
        for method in self.template.contact.methods:
            if method.key == key:
                return method
        return None

    def _confirmation_message(
        self,
        task: PendingConfirmation,
        target: FieldConfig | ContactMethodConfig,
    ) -> str:
        if task.current_value not in (None, ""):
            return (
                f"我这边看到{target.label}之前是{task.current_value}，"
                f"现在是要改成{task.proposed_value}吗？"
            )
        return f"你刚刚说的{target.label}是{task.proposed_value}，对吗？"

    def _join_responses(self, first: str, second: str) -> str:
        first = first.strip()
        second = second.strip()
        if not first:
            return second
        if not second:
            return first
        return f"{first}\n\n{second}"
