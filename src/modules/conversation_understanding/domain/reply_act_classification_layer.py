from __future__ import annotations

import re
from typing import Any

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.models import ReplyActClassificationResult


class ReplyActClassificationLayer:
    """Classify what the user is doing in this turn before field arbitration."""

    _NEW_QUESTION_PATTERNS = (
        r"有不",
        r"有吗",
        r"有没有",
        r"资源怎么样",
        r"怎么收费",
        r"靠谱吗",
        r"怎么安排",
    )

    _CORRECTION_PATTERNS = (
        r"不是.*是",
        r"说错",
        r"搞错",
        r"改成",
        r"改为",
    )

    def classify(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        question_state: dict[str, Any] | None,
    ) -> ReplyActClassificationResult:
        message = str(turn_input.user_message or "").strip()
        normalized_state = dict(question_state or {})
        asked_fields = [
            str(item).strip()
            for item in normalized_state.get("asked_fields", [])
            if str(item).strip()
        ]
        allow_mixed = bool(normalized_state.get("allow_mixed_answer", False))

        if semantic_result.primary_turn_type == "correction" or any(re.search(pattern, message) for pattern in self._CORRECTION_PATTERNS):
            return ReplyActClassificationResult(reply_act="correction", confidence=0.96, reason="explicit_correction")

        if semantic_result.primary_turn_type == "contact_answer":
            return ReplyActClassificationResult(reply_act="contact_answer", confidence=0.96, reason="contact_context")

        if semantic_result.primary_turn_type == "invalid_input" and semantic_result.subtype == "soft_refusal_current_field":
            return ReplyActClassificationResult(reply_act="soft_refusal", confidence=0.92, reason="soft_refusal_current_field")

        if semantic_result.resolved_slots and self._looks_like_preference_statement(message):
            resolved_fields = set((semantic_result.resolved_slots or {}).keys())
            partner_fields = {"partner_requirement", "partner_gender_preference"}
            self_fields = resolved_fields - partner_fields
            if resolved_fields & partner_fields and self_fields:
                return ReplyActClassificationResult(
                    reply_act="mixed_answer",
                    confidence=0.84,
                    reason="preference_markers_with_self_payload",
                )
            return ReplyActClassificationResult(reply_act="preference_statement", confidence=0.8, reason="preference_markers")

        if semantic_result.primary_turn_type in {"opening", "profile_answer", "confirmation"}:
            resolved_fields = set((semantic_result.resolved_slots or {}).keys())
            if asked_fields:
                overlap = resolved_fields & set(asked_fields)
                if overlap and len(resolved_fields - set(asked_fields)) <= 1:
                    return ReplyActClassificationResult(reply_act="direct_answer", confidence=0.9, reason="asked_field_overlap")
                if overlap and allow_mixed:
                    return ReplyActClassificationResult(reply_act="mixed_answer", confidence=0.88, reason="asked_field_overlap_with_extra")
                if resolved_fields and not overlap:
                    return ReplyActClassificationResult(reply_act="off_target_answer", confidence=0.82, reason="resolved_slots_outside_asked_fields")
            if semantic_result.resolved_slots:
                if len(semantic_result.resolved_slots) >= 2:
                    return ReplyActClassificationResult(reply_act="mixed_answer", confidence=0.78, reason="multi_slot_payload")
                if semantic_result.primary_turn_type == "profile_answer":
                    return ReplyActClassificationResult(reply_act="direct_answer", confidence=0.76, reason="single_profile_slot")

        if semantic_result.primary_turn_type == "faq_concern" or any(re.search(pattern, message) for pattern in self._NEW_QUESTION_PATTERNS):
            if semantic_result.resolved_slots:
                return ReplyActClassificationResult(reply_act="mixed_answer", confidence=0.74, reason="question_signal_with_payload")
            return ReplyActClassificationResult(reply_act="new_question", confidence=0.86, reason="question_signal")

        return ReplyActClassificationResult(reply_act="unknown", confidence=0.4, reason="fallback")

    @staticmethod
    def _looks_like_preference_statement(message: str) -> bool:
        compact = re.sub(r"\s+", "", str(message or ""))
        if not compact:
            return False
        return bool(re.search(r"(想找|希望|喜欢|偏向|偏好|倾向|要求).{0,20}", compact))
