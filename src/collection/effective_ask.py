"""有效询问计数规则。

有效询问不是“AI 问出口就立刻计数”，而是等用户下一轮回应后，
判断上一轮问题是否真的消耗了一次字段追问机会。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.faq import FAQMatch
from src.understanding import TurnSemanticFrame


@dataclass(frozen=True)
class EffectiveAskResolution:
    increment_fields: set[str] = field(default_factory=set)
    reason: str = "no_pending_ask"


class EffectiveAskResolver:
    def resolve(
        self,
        *,
        pending_field_key: str | None,
        collected_this_turn: dict[str, object],
        skipped_fields: set[str],
        semantic_frame: TurnSemanticFrame | None,
        faq_match: FAQMatch | None,
        user_message: str,
    ) -> EffectiveAskResolution:
        if not pending_field_key:
            return EffectiveAskResolution()
        if pending_field_key in collected_this_turn:
            return EffectiveAskResolution(reason="answered_field")
        if pending_field_key in skipped_fields:
            return EffectiveAskResolution(
                increment_fields={pending_field_key},
                reason="field_refused_or_skipped",
            )
        if self._is_question_or_concern(
            user_message=user_message,
            semantic_frame=semantic_frame,
            faq_match=faq_match,
        ):
            return EffectiveAskResolution(reason="interrupted_by_question_or_concern")
        if self._is_non_response(user_message):
            return EffectiveAskResolution(
                increment_fields={pending_field_key},
                reason="non_response_to_field",
            )
        return EffectiveAskResolution(
            increment_fields={pending_field_key},
            reason="answered_other_content",
        )

    def _is_question_or_concern(
        self,
        *,
        user_message: str,
        semantic_frame: TurnSemanticFrame | None,
        faq_match: FAQMatch | None,
    ) -> bool:
        if faq_match is not None:
            return True
        if semantic_frame is not None and semantic_frame.has_intent(
            "faq",
            "question",
            "concern",
            "objection",
        ):
            return True
        text = user_message.strip()
        question_markers = (
            "?",
            "？",
            "吗",
            "么",
            "怎么",
            "为什么",
            "收费",
            "价格",
            "多少钱",
            "靠谱吗",
            "隐私",
            "泄露",
        )
        return any(marker in text for marker in question_markers)

    def _is_non_response(self, user_message: str) -> bool:
        text = user_message.strip().lower()
        return text in {"嗯", "嗯嗯", "好", "好的", "对", "可以", "ok", "哦", "行"}
