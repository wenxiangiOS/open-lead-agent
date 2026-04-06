from __future__ import annotations

import logging
import re

from src.modules.conversation.domain.turn_understanding_models import (
    BlockedSlot,
    SlotCandidate,
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.slot_governance_rules import (
    extract_explicit_correction_fields,
    is_sex_confirmation_context,
    message_has_explicit_age_semantics,
)

logger = logging.getLogger(__name__)


class ContextualSlotGovernanceLayer:
    """Post-understanding field governance.

    This layer runs after lexical/semantic/AI understanding and ensures the
    final resolved slots still obey the active dialogue context.
    """

    def __init__(self, semantic_service) -> None:
        self.semantic_service = semantic_service

    def govern(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        result: TurnUnderstandingResult,
    ) -> TurnUnderstandingResult:
        governed = TurnUnderstandingResult(
            primary_turn_type=result.primary_turn_type,
            subtype=result.subtype,
            complaint_reason=result.complaint_reason,
            resume_profile_collection=result.resume_profile_collection,
            post_answer_reentry=result.post_answer_reentry,
            secondary_signals=list(result.secondary_signals or []),
            risk_flags=list(result.risk_flags or []),
            slot_candidates=dict(result.slot_candidates or {}),
            resolved_slots=dict(result.resolved_slots or {}),
            blocked_slots=dict(result.blocked_slots or {}),
            answer_first=result.answer_first,
            resume_hint=result.resume_hint,
            context_ack_type=result.context_ack_type,
            context_ack_payload=dict(result.context_ack_payload or {}),
            context_ack_occupation=result.context_ack_occupation,
            context_ack_location=result.context_ack_location,
            context_ack_preference=result.context_ack_preference,
            context_ack_field_ack=result.context_ack_field_ack,
            soft_retry_field=result.soft_retry_field,
            pre_generation_resolution=result.pre_generation_resolution,
            confidence=result.confidence,
            notes=list(result.notes or []),
        )

        message = str(turn_input.user_message or "").strip()
        last_response = str(turn_input.last_response or "").strip()
        source_text = message

        explicit_corrections = self._extract_explicit_correction_fields(
            turn_input=turn_input,
            message=message,
        )
        for field_name, value in explicit_corrections.items():
            governed.resolved_slots[field_name] = value
            governed.slot_candidates[field_name] = self._build_slot_candidate(value=value, source_text=source_text)

        self._apply_contact_context_suppression(turn_input=turn_input, result=governed, source_text=source_text)
        self._apply_sex_confirmation_backfill(
            turn_input=turn_input,
            result=governed,
            message=message,
            last_response=last_response,
            source_text=source_text,
        )
        self._apply_field_conflict_resolution(
            turn_input=turn_input,
            result=governed,
            message=message,
            source_text=source_text,
            last_response=last_response,
        )
        if explicit_corrections:
            governed.notes.append(f"contextual_governance=explicit_correction:{','.join(sorted(explicit_corrections))}")
        return governed

    def govern_raw_fields(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        raw_fields: dict[str, str],
        message: str,
        last_response: str,
    ) -> tuple[dict[str, str], dict[str, BlockedSlot]]:
        governed = dict(raw_fields or {})
        blocked: dict[str, BlockedSlot] = {}
        source_text = str(message or "").strip()

        explicit_corrections = self._extract_explicit_correction_fields(
            turn_input=turn_input,
            message=message,
        )
        if explicit_corrections:
            governed.update(explicit_corrections)

        confirmation_context_sex = self.semantic_service._extract_confirmed_sex_candidate_from_context(last_response)  # noqa: SLF001
        sex_question_context = is_sex_confirmation_context(
            last_response=last_response,
            pending_confirmation_field=getattr(turn_input, "pending_confirmation_field", None),
            confirmed_sex_candidate=confirmation_context_sex,
        )
        if sex_question_context and "sex" not in governed:
            embedded = re.search(
                r"(?:^|[，,、 ]|是|就是)\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?(?:$|[，,。！？!? ])",
                message,
            )
            affirmative = re.search(
                r"^\s*(?:是的|对|对的|嗯|嗯嗯|好的|好|没错)"
                r"(?:[呀呢啊哦哈啦嘛]*)?\s*(男生|女生|男的|女的|男|女)"
                r"(?:\s*[，,、 ]\s*.*)?$",
                message,
            )
            sex_match = embedded or affirmative
            if sex_match:
                governed["sex"] = "男" if "男" in sex_match.group(1) else "女"

        compact_message = re.sub(r"\s+", "", str(message or ""))
        if bool(getattr(turn_input, "in_contact_flow", False)):
            looks_like_numeric_contact_attempt = bool(re.fullmatch(r"(?:\+?86)?[\d\s-]{7,17}", compact_message))
            if looks_like_numeric_contact_attempt and not message_has_explicit_age_semantics(message):
                governed.pop("age", None)
                governed.pop("age_label", None)

        occupation_value = str(governed.get("occupation") or "").strip()
        if occupation_value and occupation_value in {"单身", "单身呢", "未婚", "离异", "已婚"}:
            blocked["occupation"] = BlockedSlot(
                value=occupation_value,
                reason="looks_like_marital_status_not_occupation",
                source="governance",
                source_text=source_text,
            )
            governed.pop("occupation", None)

        if (
            sex_question_context
            and "sex" in governed
            and "partner_gender_preference" in governed
            and not re.search(r"(找|想找|喜欢|偏好|偏向).{0,4}(男生|女生|男的|女的|男|女)", message)
        ):
            blocked["partner_gender_preference"] = BlockedSlot(
                value=str(governed["partner_gender_preference"]).strip(),
                reason="sex_confirmation_context_prefers_self_sex",
                source="governance",
                source_text=source_text,
            )
            governed.pop("partner_gender_preference", None)

        if explicit_corrections:
            logger.info(
                "[提取保护] 显式纠正命中，优先放行字段: %s",
                ",".join(sorted(explicit_corrections)),
            )

        return governed, blocked

    @staticmethod
    def _build_slot_candidate(*, value: str, source_text: str):
        return SlotCandidate(
            value=str(value or "").strip(),
            confidence=0.9,
            source="governance",
            source_text=source_text,
        )

    def _extract_explicit_correction_fields(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        message: str,
    ) -> dict[str, str]:
        return extract_explicit_correction_fields(
            message=message,
            user_profile=getattr(turn_input, "user_profile", None),
            deterministic_extractor=self.semantic_service._extract_deterministic_profile_fields,  # noqa: SLF001
            looks_like_correction=self.semantic_service._looks_like_correction,  # noqa: SLF001
        )

    def _apply_contact_context_suppression(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        result: TurnUnderstandingResult,
        source_text: str,
    ) -> None:
        if not bool(getattr(turn_input, "in_contact_flow", False)):
            return
        compact_message = re.sub(r"\s+", "", str(turn_input.user_message or ""))
        looks_like_numeric_contact_attempt = bool(re.fullmatch(r"(?:\+?86)?[\d\s-]{7,17}", compact_message))
        if not looks_like_numeric_contact_attempt:
            return
        if message_has_explicit_age_semantics(source_text):
            return
        self._block_field(result, "age", "contact_context_prefers_contact_over_age", source_text)
        self._block_field(result, "age_label", "contact_context_prefers_contact_over_age", source_text)

    def _apply_sex_confirmation_backfill(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        result: TurnUnderstandingResult,
        message: str,
        last_response: str,
        source_text: str,
    ) -> None:
        if "sex" in result.resolved_slots:
            return
        confirmation_context_sex = self.semantic_service._extract_confirmed_sex_candidate_from_context(last_response)  # noqa: SLF001
        sex_question_context = is_sex_confirmation_context(
            last_response=last_response,
            pending_confirmation_field=getattr(turn_input, "pending_confirmation_field", None),
            confirmed_sex_candidate=confirmation_context_sex,
        )
        if not sex_question_context:
            return
        embedded = re.search(
            r"(?:^|[，,、 ]|是|就是)\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?(?:$|[，,。！？!? ])",
            message,
        )
        if not embedded:
            return
        sex = "男" if "男" in embedded.group(1) else "女"
        result.resolved_slots["sex"] = sex
        result.slot_candidates["sex"] = self._build_slot_candidate(value=sex, source_text=source_text)

    def _apply_field_conflict_resolution(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        result: TurnUnderstandingResult,
        message: str,
        source_text: str,
        last_response: str,
    ) -> None:
        occupation_value = str(result.resolved_slots.get("occupation") or "").strip()
        if occupation_value in {"单身", "单身呢", "未婚", "离异", "已婚"}:
            self._block_field(result, "occupation", "looks_like_marital_status_not_occupation", source_text)

        sex_confirmation_context = is_sex_confirmation_context(
            last_response=last_response,
            pending_confirmation_field=getattr(turn_input, "pending_confirmation_field", None),
            confirmed_sex_candidate=self.semantic_service._extract_confirmed_sex_candidate_from_context(last_response),  # noqa: SLF001
        )
        if (
            sex_confirmation_context
            and "sex" in result.resolved_slots
            and "partner_gender_preference" in result.resolved_slots
            and not re.search(r"(找|想找|喜欢|偏好|偏向).{0,4}(男生|女生|男的|女的|男|女)", message)
        ):
            self._block_field(
                result,
                "partner_gender_preference",
                "sex_confirmation_context_prefers_self_sex",
                source_text,
            )

    def _block_field(
        self,
        result: TurnUnderstandingResult,
        field_name: str,
        reason: str,
        source_text: str,
    ) -> None:
        value = result.resolved_slots.pop(field_name, None)
        result.slot_candidates.pop(field_name, None)
        if value is None:
            return
        result.blocked_slots[field_name] = BlockedSlot(
            value=str(value).strip(),
            reason=reason,
            source="governance",
            source_text=source_text,
        )
