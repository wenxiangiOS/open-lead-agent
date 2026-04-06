from __future__ import annotations

from .models import AIDisplayResponse, AIGenerationDraft, AIResponseValidationResult


class ResponseDeliveryService:
    """Freeze the final display response once cleanup completes."""

    def deliver(
        self,
        *,
        draft: AIGenerationDraft,
        validation_result: AIResponseValidationResult,
        cleaned_response: str,
        safe_cleaned: bool,
        fallback_response: str = "",
    ) -> AIDisplayResponse:
        fallback_used = bool(validation_result.should_fallback)
        display_response = str(fallback_response if fallback_used else cleaned_response or "")
        return AIDisplayResponse(
            display_response=display_response,
            raw_ai_response=draft.raw_ai_response,
            safe_cleaned=safe_cleaned,
            fallback_used=fallback_used,
            fallback_reason=validation_result.fallback_reason,
        )
