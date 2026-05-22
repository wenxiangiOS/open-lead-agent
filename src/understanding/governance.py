"""上下文字段治理。

这一层运行在“模型/规则提取出字段观察”之后、“字段接受入档”之前。
它不做字段提取，也不生成回复，只根据当前轮语境决定哪些字段观察可以继续进入提交计划。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.templates.config import TemplateConfig
from src.understanding.context import configured_item_map
from src.understanding.models import FieldObservation, PersistencePlan, TurnSemanticFrame


@dataclass(frozen=True)
class FieldGovernanceResult:
    frame: TurnSemanticFrame
    blocked_observations: list[FieldObservation] = field(default_factory=list)


class FieldGovernanceService:
    """按上下文过滤字段观察，避免错槽字段进入 acceptance。"""

    _FAQ_INTENTS = {"faq", "question", "concern", "objection"}
    _PROFILE_INTENTS = {"profile", "profile_answer", "self_profile"}
    _CONTACT_REPLY_ACTS = {"contact", "contact_answer", "leave_contact"}

    def __init__(self, template: TemplateConfig):
        self.template = template

    def govern(
        self,
        frame: TurnSemanticFrame,
        *,
        expected_field: str = "",
        user_message: str = "",
    ) -> FieldGovernanceResult:
        if not self.template.field_permissions.enabled or not frame.observations:
            return FieldGovernanceResult(frame=frame)

        configured = configured_item_map(self.template)
        profile_fields = {field.key for field in self.template.fields if field.extract}
        contact_fields = {method.key for method in self.template.contact.methods if method.extract}
        all_fields = set(configured)
        expected_field = str(expected_field or "").strip()

        allowed_fields: set[str] = set()
        blocked_fields: set[str] = set()
        reasons: dict[str, str] = {}

        self._apply_builtin_rules(
            frame=frame,
            expected_field=expected_field,
            user_message=user_message,
            profile_fields=profile_fields,
            contact_fields=contact_fields,
            allowed_fields=allowed_fields,
            blocked_fields=blocked_fields,
            reasons=reasons,
        )
        self._apply_template_rules(
            frame=frame,
            expected_field=expected_field,
            all_fields=all_fields,
            allowed_fields=allowed_fields,
            blocked_fields=blocked_fields,
            reasons=reasons,
        )

        kept: list[FieldObservation] = []
        blocked: list[FieldObservation] = []
        for observation in frame.observations:
            field_name = str(observation.field or "").strip()
            field_blocked = field_name in blocked_fields
            field_not_allowed = allowed_fields and field_name not in allowed_fields
            if field_blocked or field_not_allowed:
                reason = reasons.get(field_name, "field_permission_blocked")
                blocked.append(self._replace_reason(observation, reason))
                continue
            kept.append(observation)

        if not blocked:
            return FieldGovernanceResult(frame=frame)

        blocked_field_names = {item.field for item in blocked}
        governed_frame = TurnSemanticFrame(
            intents=frame.intents,
            observations=kept,
            turn_mode=frame.turn_mode,
            no_reask_fields=[
                field for field in frame.no_reask_fields if field not in blocked_field_names
            ],
            faq_intent=frame.faq_intent,
            compliance_signals=frame.compliance_signals,
            reply_act=frame.reply_act,
            confidence=frame.confidence,
            raw_payload=frame.raw_payload,
        )
        return FieldGovernanceResult(frame=governed_frame, blocked_observations=blocked)

    def merge_blocked_into_plan(
        self,
        plan: PersistencePlan,
        blocked_observations: list[FieldObservation],
    ) -> PersistencePlan:
        if not blocked_observations:
            return plan
        rejected = dict(plan.rejected_fields)
        for observation in blocked_observations:
            rejected[observation.field] = observation.value
        return PersistencePlan(
            accepted_fields=dict(plan.accepted_fields),
            provisional_fields=dict(plan.provisional_fields),
            pending_fields=dict(plan.pending_fields),
            rejected_fields=rejected,
            observation_log=[*blocked_observations, *plan.observation_log],
        )

    def _apply_builtin_rules(
        self,
        *,
        frame: TurnSemanticFrame,
        expected_field: str,
        user_message: str,
        profile_fields: set[str],
        contact_fields: set[str],
        allowed_fields: set[str],
        blocked_fields: set[str],
        reasons: dict[str, str],
    ) -> None:
        if (
            self.template.field_permissions.faq_blocks_fields_by_default
            and self._is_faq_only_turn(frame)
        ):
            blocked_fields.update(profile_fields | contact_fields)
            self._mark_reason(
                reasons,
                profile_fields | contact_fields,
                "faq_turn_blocks_field_write",
            )
            return

        if (
            self.template.field_permissions.contact_context_blocks_profile_fields
            and self._is_contact_context(frame, expected_field)
            and not self._has_profile_intent(frame)
        ):
            allowed_fields.update(contact_fields)
            blocked_fields.update(profile_fields)
            self._mark_reason(reasons, profile_fields, "contact_context_blocks_profile_fields")

        if (
            self.template.field_permissions.short_answer_binds_to_expected_field
            and expected_field
            and expected_field in profile_fields | contact_fields
            and self._looks_like_short_answer(user_message)
            and not self._is_question_or_concern(frame, user_message)
        ):
            allowed_fields.clear()
            allowed_fields.add(expected_field)
            blocked_candidates = (profile_fields | contact_fields) - {expected_field}
            blocked_fields.update(blocked_candidates)
            self._mark_reason(reasons, blocked_candidates, "short_answer_bound_to_expected_field")

    def _apply_template_rules(
        self,
        *,
        frame: TurnSemanticFrame,
        expected_field: str,
        all_fields: set[str],
        allowed_fields: set[str],
        blocked_fields: set[str],
        reasons: dict[str, str],
    ) -> None:
        for rule in self.template.field_permissions.rules:
            if not self._rule_matches(rule, frame=frame, expected_field=expected_field):
                continue
            rule_allowed = {field for field in rule.allow_fields if field in all_fields}
            rule_blocked = {field for field in rule.block_fields if field in all_fields}
            if rule_allowed:
                allowed_fields.update(rule_allowed)
                if not rule.allow_mixed_answer:
                    blocked_fields.update(all_fields - rule_allowed)
                    self._mark_reason(
                        reasons,
                        all_fields - rule_allowed,
                        rule.reason or rule.name or "template_field_permission_rule",
                    )
            if rule_blocked:
                blocked_fields.update(rule_blocked)
                self._mark_reason(
                    reasons,
                    rule_blocked,
                    rule.reason or rule.name or "template_field_permission_rule",
                )

    def _rule_matches(self, rule, *, frame: TurnSemanticFrame, expected_field: str) -> bool:
        has_condition = bool(rule.intents or rule.reply_acts or rule.expected_fields)
        if not has_condition:
            return False
        intents = {item.strip().lower() for item in frame.intents}
        rule_intents = {item.strip().lower() for item in rule.intents}
        if rule.intents and not intents.intersection(rule_intents):
            return False
        if rule.reply_acts and frame.reply_act.strip().lower() not in {
            item.strip().lower() for item in rule.reply_acts
        }:
            return False
        if rule.expected_fields and expected_field not in set(rule.expected_fields):
            return False
        return True

    def _is_faq_only_turn(self, frame: TurnSemanticFrame) -> bool:
        return self._is_question_or_concern(frame, "") and not (
            self._has_profile_intent(frame) or frame.has_contact_intent
        )

    def _is_question_or_concern(self, frame: TurnSemanticFrame, user_message: str) -> bool:
        if frame.faq_intent:
            return True
        if frame.has_intent(*self._FAQ_INTENTS):
            return True
        text = user_message.strip()
        question_markers = ("?", "？", "怎么", "为什么", "收费", "价格", "隐私", "靠谱吗")
        return any(marker in text for marker in question_markers)

    def _has_profile_intent(self, frame: TurnSemanticFrame) -> bool:
        return frame.has_intent(*self._PROFILE_INTENTS)

    def _is_contact_context(self, frame: TurnSemanticFrame, expected_field: str) -> bool:
        contact_fields = {method.key for method in self.template.contact.methods if method.extract}
        if expected_field in contact_fields:
            return True
        if frame.has_contact_intent:
            return True
        return frame.reply_act.strip().lower() in self._CONTACT_REPLY_ACTS

    def _looks_like_short_answer(self, user_message: str) -> bool:
        text = user_message.strip()
        if not text:
            return False
        return len(text) <= 18

    def _mark_reason(self, reasons: dict[str, str], fields: set[str], reason: str) -> None:
        for field_name in fields:
            reasons.setdefault(field_name, reason)

    def _replace_reason(self, observation: FieldObservation, reason: str) -> FieldObservation:
        return FieldObservation(
            field=observation.field,
            value=observation.value,
            normalized_value=observation.normalized_value,
            scope=observation.scope,
            owner=observation.owner,
            evidence_text=observation.evidence_text,
            confidence=observation.confidence,
            write_mode=observation.write_mode,
            source=observation.source,
            reason=reason,
        )
