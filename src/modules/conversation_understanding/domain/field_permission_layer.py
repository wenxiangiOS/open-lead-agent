from __future__ import annotations

from typing import Any

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.models import (
    FieldPermissionResult,
    ReplyActClassificationResult,
)


class FieldPermissionLayer:
    """Decide which fields are allowed to survive in the current context."""

    _HIGH_CONFIDENCE_EXTRA_FIELDS = {"occupation", "location", "education", "marital_status", "monthly_income"}
    _INCOME_RISK_BLOCKS = {"age", "age_label", "phone", "wechat", "partner_requirement"}
    _OCCUPATION_RISK_BLOCKS = {"age", "age_label", "phone", "wechat", "partner_requirement"}
    _EDUCATION_RISK_BLOCKS = {"age", "age_label", "phone", "wechat", "partner_requirement"}
    _MARITAL_RISK_BLOCKS = {"age", "age_label", "phone", "wechat", "partner_requirement"}
    _CONTACT_ONLY_FIELDS = {"phone", "wechat", "contact"}
    _PARTNER_ONLY_FIELDS = {"partner_requirement", "partner_gender_preference"}

    @staticmethod
    def _looks_like_contact_preference_or_refusal(message: str) -> bool:
        compact = "".join(str(message or "").split())
        if not compact:
            return False
        if "微信就可以" in compact or "微信就行" in compact or "留微信就好" in compact or "不留电话" in compact:
            return True
        has_contact_marker = any(token in compact.lower() for token in ("wx", "weixin")) or any(
            token in compact for token in ("微信", "电话", "手机", "手机号", "号码", "联系")
        )
        if not has_contact_marker:
            return False
        return any(
            token in compact
            for token in ("不留", "不留了", "先不留", "不给", "不给了", "先不给", "不方便给", "不方便留", "就可以", "就行", "就好")
        )

    @staticmethod
    def _result_fields(result: TurnUnderstandingResult) -> set[str]:
        fields = set((result.slot_candidates or {}).keys())
        if fields:
            return fields
        return set((result.resolved_slots or {}).keys())

    def decide(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        reply_act_result: ReplyActClassificationResult,
        question_state: dict[str, Any] | None,
    ) -> FieldPermissionResult:
        normalized_state = dict(question_state or {})
        asked_fields = {
            str(item).strip()
            for item in normalized_state.get("asked_fields", [])
            if str(item).strip()
        }
        side_fields = {
            str(item).strip()
            for item in normalized_state.get("side_fields", [])
            if str(item).strip()
        }
        expected_scope = str(normalized_state.get("expected_scope") or "mixed").strip() or "mixed"
        allow_mixed = bool(normalized_state.get("allow_mixed_answer", False))
        message = str(getattr(turn_input, "user_message", "") or "").strip()
        contact_only_turn = bool(
            semantic_result.primary_turn_type == "contact_answer"
            or reply_act_result.reply_act == "contact_answer"
            or (
                getattr(turn_input, "in_contact_flow", False)
                and (
                    ((asked_fields <= {"contact"}) if asked_fields else False)
                    or self._looks_like_contact_preference_or_refusal(message)
                    or str(getattr(semantic_result, "subtype", "") or "").strip() in {"contact_context_reply", "contact_refusal"}
                )
            )
        )

        if contact_only_turn:
            return FieldPermissionResult(
                allowed_fields=set(self._CONTACT_ONLY_FIELDS),
                blocked_fields={
                    "age",
                    "age_label",
                    "height",
                    "weight",
                    "monthly_income",
                    "occupation",
                    "location",
                    "education",
                    "marital_status",
                    "partner_requirement",
                    "partner_gender_preference",
                },
                priority_fields=["phone", "wechat"],
                allowed_scope="contact",
                allow_mixed_answer=False,
            )

        if semantic_result.primary_turn_type == "faq_concern":
            return FieldPermissionResult(
                allowed_fields=set(),
                blocked_fields=self._result_fields(semantic_result),
                priority_fields=[],
                allowed_scope="faq",
                allow_mixed_answer=False,
            )

        if reply_act_result.reply_act == "preference_statement":
            return FieldPermissionResult(
                allowed_fields=set(self._PARTNER_ONLY_FIELDS),
                blocked_fields={"sex", "age", "location", "education", "occupation", "marital_status", "monthly_income"},
                priority_fields=["partner_requirement", "partner_gender_preference"],
                allowed_scope="partner",
                allow_mixed_answer=False,
            )

        if reply_act_result.reply_act == "new_question":
            return FieldPermissionResult(
                allowed_fields=set(),
                blocked_fields=self._result_fields(semantic_result),
                priority_fields=[],
                allowed_scope=expected_scope,
                allow_mixed_answer=False,
            )

        allowed = set(asked_fields) | set(side_fields)
        blocked = set()
        priority = list(asked_fields) or list(side_fields)

        if reply_act_result.reply_act == "correction":
            correction_fields = self._result_fields(semantic_result)
            return FieldPermissionResult(
                allowed_fields=correction_fields,
                blocked_fields=set(),
                priority_fields=list(correction_fields),
                allowed_scope="mixed",
                allow_mixed_answer=True,
            )

        if not allowed:
            allowed = self._result_fields(semantic_result)

        if reply_act_result.reply_act == "mixed_answer":
            allowed |= {field for field in self._HIGH_CONFIDENCE_EXTRA_FIELDS if field not in self._PARTNER_ONLY_FIELDS}
        elif reply_act_result.reply_act == "direct_answer":
            if "monthly_income" in asked_fields:
                blocked |= set(self._INCOME_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"occupation", "location"}
            if "occupation" in asked_fields and allow_mixed:
                allowed |= {"monthly_income", "location"}
            elif "occupation" in asked_fields:
                blocked |= set(self._OCCUPATION_RISK_BLOCKS)
            if "location" in asked_fields and allow_mixed:
                allowed |= {"monthly_income", "occupation"}
            if "education" in asked_fields:
                blocked |= set(self._EDUCATION_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"occupation", "marital_status"}
            if "marital_status" in asked_fields:
                blocked |= set(self._MARITAL_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"education"}
        elif reply_act_result.reply_act == "off_target_answer":
            allowed = self._result_fields(semantic_result)
            blocked = set(asked_fields) - allowed

        return FieldPermissionResult(
            allowed_fields=allowed,
            blocked_fields=blocked,
            priority_fields=priority,
            allowed_scope=expected_scope,
            allow_mixed_answer=allow_mixed,
        )

    def filter_result(
        self,
        *,
        result: TurnUnderstandingResult,
        permission_result: FieldPermissionResult,
    ) -> TurnUnderstandingResult:
        allowed = set(permission_result.allowed_fields or set())
        blocked = set(permission_result.blocked_fields or set())
        if not allowed and not blocked:
            return result

        new_resolved = dict(result.resolved_slots or {})
        new_candidates = dict(result.slot_candidates or {})
        new_blocked = dict(result.blocked_slots or {})

        for field in list(new_resolved.keys()):
            if field in blocked or (allowed and field not in allowed):
                value = new_resolved.pop(field, None)
                new_candidates.pop(field, None)
                if value is not None and field not in new_blocked:
                    from src.modules.conversation.domain.turn_understanding_models import BlockedSlot

                    new_blocked[field] = BlockedSlot(
                        value=str(value).strip(),
                        reason="field_permission_filtered",
                        source="field_permission",
                        source_text=str((result.slot_candidates.get(field).source_text if result.slot_candidates.get(field) else "") or ""),
                    )

        result.resolved_slots = new_resolved
        result.slot_candidates = new_candidates
        result.blocked_slots = new_blocked
        return result
