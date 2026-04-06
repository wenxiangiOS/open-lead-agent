from __future__ import annotations

from .models import AIGenerationDraft


class ResponseDraftService:
    """Freeze the first AI draft before any rule-based rewrite can happen."""

    def build(
        self,
        *,
        raw_ai_response: str,
        response_plan_id: str | None = None,
        generation_source: str = "ai",
    ) -> AIGenerationDraft:
        return AIGenerationDraft(
            raw_ai_response=str(raw_ai_response or ""),
            generation_source=generation_source,
            response_plan_id=response_plan_id,
        )
