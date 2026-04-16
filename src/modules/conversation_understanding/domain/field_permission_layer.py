from __future__ import annotations

import re

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
    def _looks_like_mixed_profile_payload(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        profile_markers = (
            "身高", "体重", "本科", "大专", "硕士", "博士", "单身", "未婚", "离异",
            "老师", "教师", "医生", "程序员", "在编", "深圳", "广州", "上海", "北京",
            "龙华", "南山", "福田", "河南", "老家", "深户", "有房", "有车", "找同老家",
            "90后", "95后", "98年", "180+",
        )
        numeric_pair = bool(re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text))
        return numeric_pair or sum(1 for marker in profile_markers if marker in text) >= 2

    @staticmethod
    def _looks_like_self_and_preference_mixed(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        has_preference_signal = bool(
            re.search(r"(喜欢|看重|想找|找(?:男朋友|女朋友|对象|另一半|[男女]生)|希望对方|最好|起码|至少|优先|不要)", compact)
        )
        if not has_preference_signal:
            return False
        has_self_signal = bool(
            re.search(r"(?:我|本人|自己).{0,8}(?:在|是|做|单身|未婚|离异|本科|大专|硕士|博士|收入|月薪|年薪|在编|教师|老师|医生|程序员)", compact)
            or re.search(r"(?:^|[，,。；;])(?:19\d{2}|20\d{2}|\d{2})年(?:的)?", compact)
            or re.search(r"(?:^|[，,。；;])(?:\d{2}后|90后|95后)", compact)
            or re.search(r"(?:^|[，,。；;])(?:在编(?:教师|老师)|[男女]生|男|女)(?:[，,。；;]|$)", compact)
        )
        return has_self_signal

    @staticmethod
    def _looks_like_contact_preference_or_refusal(message: str) -> bool:
        compact = "".join(str(message or "").split())
        if not compact:
            return False
        if (
            "微信就可以" in compact
            or "微信就行" in compact
            or "留微信就好" in compact
            or "不留电话" in compact
            or bool(re.search(r"微信[就久]?(?:联系)?(?:就)?(?:可|行|好)以了?", compact))
        ):
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
    def _effective_resolved_slots(result: TurnUnderstandingResult) -> dict[str, Any]:
        persistence_plan = getattr(result, "persistence_plan", None)
        resolved_slots = dict(result.resolved_slots or {})
        if persistence_plan is not None:
            resolved_slots = {}
        accepted_fields = getattr(persistence_plan, "accepted_fields", None) or []
        for field in accepted_fields:
            field_name = str(getattr(field, "field", "") or "").strip()
            if not field_name:
                continue
            resolved_slots[field_name] = getattr(field, "normalized_value", None)
        return resolved_slots

    @classmethod
    def _result_fields(cls, result: TurnUnderstandingResult) -> set[str]:
        fields = set((result.slot_candidates or {}).keys())
        if fields:
            return fields
        return set(cls._effective_resolved_slots(result).keys())

    def _resolve_preserve_mixed_extra_fields(
        self,
        *,
        message: str,
        result_fields: set[str],
        reply_act: str,
    ) -> set[str]:
        extras = set(self._CONTACT_ONLY_FIELDS)
        if (
            reply_act == "preference_statement"
            or "partner_requirement" in result_fields
            or "partner_gender_preference" in result_fields
            or self._looks_like_self_and_preference_mixed(message)
        ):
            extras |= set(self._PARTNER_ONLY_FIELDS)
        return extras

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
        result_fields = self._result_fields(semantic_result)
        mixed_profile_payload = self._looks_like_mixed_profile_payload(message) or self._looks_like_self_and_preference_mixed(message)
        preserve_mixed_semantics = mixed_profile_payload
        allow_mixed = allow_mixed or preserve_mixed_semantics
        preserve_mixed_extra_fields = self._resolve_preserve_mixed_extra_fields(
            message=message,
            result_fields=result_fields,
            reply_act=reply_act_result.reply_act,
        )
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
        ) and not preserve_mixed_semantics

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
            if preserve_mixed_semantics:
                fields = result_fields | set(preserve_mixed_extra_fields)
                return FieldPermissionResult(
                    allowed_fields=fields,
                    blocked_fields=set(),
                    priority_fields=[field for field in ("phone", "wechat", "contact") if field in fields],
                    allowed_scope="mixed",
                    allow_mixed_answer=True,
                )
            return FieldPermissionResult(
                allowed_fields=set(),
                blocked_fields=result_fields,
                priority_fields=[],
                allowed_scope="faq",
                allow_mixed_answer=False,
            )

        if reply_act_result.reply_act == "preference_statement":
            if preserve_mixed_semantics:
                fields = result_fields | set(preserve_mixed_extra_fields)
                return FieldPermissionResult(
                    allowed_fields=fields,
                    blocked_fields=set(),
                    priority_fields=list(fields),
                    allowed_scope="mixed",
                    allow_mixed_answer=True,
                )
            return FieldPermissionResult(
                allowed_fields=set(self._PARTNER_ONLY_FIELDS),
                blocked_fields={"sex", "age", "location", "education", "occupation", "marital_status", "monthly_income"},
                priority_fields=["partner_requirement", "partner_gender_preference"],
                allowed_scope="partner",
                allow_mixed_answer=False,
            )

        if reply_act_result.reply_act == "new_question":
            if preserve_mixed_semantics:
                fields = result_fields | set(preserve_mixed_extra_fields)
                return FieldPermissionResult(
                    allowed_fields=fields,
                    blocked_fields=set(),
                    priority_fields=list(fields),
                    allowed_scope="mixed",
                    allow_mixed_answer=True,
                )
            return FieldPermissionResult(
                allowed_fields=set(),
                blocked_fields=result_fields,
                priority_fields=[],
                allowed_scope=expected_scope,
                allow_mixed_answer=False,
            )

        allowed = set(asked_fields) | set(side_fields)
        blocked = set()
        priority = list(asked_fields) or list(side_fields)

        if reply_act_result.reply_act == "correction":
            correction_fields = result_fields
            return FieldPermissionResult(
                allowed_fields=correction_fields,
                blocked_fields=set(),
                priority_fields=list(correction_fields),
                allowed_scope="mixed",
                allow_mixed_answer=True,
            )

        if not allowed and preserve_mixed_semantics:
            return FieldPermissionResult(
                allowed_fields=set(),
                blocked_fields=set(),
                priority_fields=[],
                allowed_scope="mixed",
                allow_mixed_answer=True,
            )

        if not allowed:
            allowed = result_fields

        if reply_act_result.reply_act == "mixed_answer":
            allowed |= {field for field in self._HIGH_CONFIDENCE_EXTRA_FIELDS if field not in self._PARTNER_ONLY_FIELDS}
        elif reply_act_result.reply_act == "direct_answer":
            if "monthly_income" in asked_fields:
                blocked |= set(self._INCOME_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"occupation", "location", "partner_requirement", "partner_gender_preference"}
            if "occupation" in asked_fields and allow_mixed:
                allowed |= {"monthly_income", "location", "partner_requirement", "partner_gender_preference"}
            elif "occupation" in asked_fields:
                blocked |= set(self._OCCUPATION_RISK_BLOCKS)
            if "location" in asked_fields and allow_mixed:
                allowed |= {"monthly_income", "occupation", "partner_requirement"}
            if "education" in asked_fields:
                blocked |= set(self._EDUCATION_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"occupation", "marital_status", "partner_requirement"}
            if "marital_status" in asked_fields:
                blocked |= set(self._MARITAL_RISK_BLOCKS)
                if allow_mixed:
                    allowed |= {"education", "partner_requirement"}
        elif reply_act_result.reply_act == "off_target_answer":
            allowed = result_fields
            blocked = set(asked_fields) - allowed

        if preserve_mixed_semantics:
            allowed |= result_fields | set(preserve_mixed_extra_fields)
            blocked -= result_fields
            expected_scope = "mixed"

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

        new_resolved = self._effective_resolved_slots(result)
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
