from __future__ import annotations

import logging
from typing import Any

from .models import AIDisplayResponse, AIGenerationDraft, AIResponseValidationResult

logger = logging.getLogger(__name__)


class ResponseObservabilityService:
    """Record every stage so the final display text is auditable."""

    def build_record(
        self,
        *,
        draft: AIGenerationDraft,
        validation_result: AIResponseValidationResult,
        cleaned_response: str,
        delivery: AIDisplayResponse,
        extracted_fields_count: int = 0,
        decision_after_collection: Any = None,
    ) -> dict[str, Any]:
        return {
            "raw_ai_response": draft.raw_ai_response,
            "validated_response": draft.raw_ai_response,
            "cleaned_response": cleaned_response,
            "final_display_response": delivery.display_response,
            "delivery_status": validation_result.delivery_status,
            "violations": list(validation_result.violations),
            "warnings": list(validation_result.warnings),
            "fallback_triggered": delivery.fallback_used,
            "fallback_reason": delivery.fallback_reason,
            "safe_cleanup_applied": delivery.safe_cleaned,
            "extracted_fields": extracted_fields_count,
            "decision_after_collection": (
                decision_after_collection.to_log_dict()
                if hasattr(decision_after_collection, "to_log_dict")
                else str(decision_after_collection or "")
            ),
        }

    def log(self, *, account_id: str, record: dict[str, Any]) -> None:
        raw_response = str(record.get("raw_ai_response") or "")
        final_response = str(record.get("final_display_response") or "")
        logger.info(
            "[ai_response_unified] account_id=%s delivery_status=%s safe_cleanup=%s fallback=%s raw_len=%s final_len=%s reason=%s",
            account_id,
            record.get("delivery_status"),
            int(bool(record.get("safe_cleanup_applied"))),
            int(bool(record.get("fallback_triggered"))),
            len(raw_response),
            len(final_response),
            record.get("fallback_reason") or "-",
        )
        if raw_response != final_response:
            logger.info(
                "[ai_response_unified.diff] account_id=%s raw=%r final=%r",
                account_id,
                raw_response,
                final_response,
            )
