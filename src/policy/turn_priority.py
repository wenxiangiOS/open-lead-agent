"""单轮优先级策略。

这个模块只回答“本轮前台优先处理什么”，不解析用户原文，也不生成回复。
行业内容来自 FAQ、合规和模板配置；这里保持通用优先级。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.collection.confirmation import PendingConfirmation
from src.faq import FAQMatch
from src.templates.config import ContactMethodConfig, FieldConfig
from src.understanding import TurnSemanticFrame


@dataclass(frozen=True)
class TurnPriority:
    task: str
    reason: str


class TurnPriorityPolicy:
    def decide(
        self,
        *,
        semantic_frame: TurnSemanticFrame | None,
        faq_match: FAQMatch | None,
        pending_confirmation: PendingConfirmation | None,
        next_field: FieldConfig | None,
        contact_method: ContactMethodConfig | None,
        early_closing_ready: bool,
    ) -> TurnPriority:
        if pending_confirmation is not None:
            return TurnPriority("pending_confirmation", "pending_confirmation")

        if semantic_frame is not None and semantic_frame.wants_to_stop:
            return TurnPriority("conversation_end", "semantic:conversation_end")

        if self._has_question_or_concern(semantic_frame, faq_match):
            reason = f"faq:{faq_match.intent}" if faq_match is not None else "semantic:question"
            return TurnPriority("answer_question", reason)

        if early_closing_ready:
            return TurnPriority("closing", "closing_ready")

        if contact_method is not None:
            if semantic_frame is not None and semantic_frame.has_contact_intent:
                return TurnPriority("contact_capture", "semantic:contact_intent")
            return TurnPriority("contact_capture", "contact_ready")

        if next_field is not None:
            return TurnPriority("profile_collection", "profile_collection")

        return TurnPriority("no_action", "no_next_action")

    def _has_question_or_concern(
        self,
        semantic_frame: TurnSemanticFrame | None,
        faq_match: FAQMatch | None,
    ) -> bool:
        if faq_match is not None:
            return True
        if semantic_frame is None:
            return False
        return semantic_frame.has_intent("faq", "question", "concern", "objection")
