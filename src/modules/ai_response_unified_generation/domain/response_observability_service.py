from __future__ import annotations

from datetime import datetime, timezone
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
        display_mutation_count: int = 0,
        display_mutation_source: str = "",
        post_freeze_write_attempt: bool = False,
        raw_display_diff_reason: str = "",
    ) -> dict[str, Any]:
        raw_response = str(draft.raw_ai_response or "")
        final_response = str(delivery.display_response or "")
        raw_display_diff = raw_response != final_response
        if not raw_display_diff_reason and raw_display_diff:
            if delivery.fallback_used:
                raw_display_diff_reason = f"fallback:{delivery.fallback_reason or 'unknown'}"
            elif str(cleaned_response or "") != raw_response:
                raw_display_diff_reason = "safe_cleanup"
            else:
                raw_display_diff_reason = "unknown"
        return {
            "raw_ai_response": raw_response,
            "validated_response": raw_response,
            "cleaned_response": cleaned_response,
            "display_response": final_response,
            "final_display_response": final_response,
            "delivery_status": validation_result.delivery_status,
            "violations": list(validation_result.violations),
            "warnings": list(validation_result.warnings),
            "fallback_triggered": delivery.fallback_used,
            "fallback_reason": delivery.fallback_reason,
            "safe_cleanup_applied": delivery.safe_cleaned,
            "display_frozen_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "display_mutation_count": int(display_mutation_count),
            "display_mutation_source": str(display_mutation_source or ""),
            "post_freeze_write_attempt": bool(post_freeze_write_attempt),
            "post_freeze_mutation_count": int(display_mutation_count),
            "raw_display_diff": raw_display_diff,
            "raw_display_diff_reason": str(raw_display_diff_reason or ("none" if not raw_display_diff else "unknown")),
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
                "[ai_response_unified.diff] account_id=%s reason=%s raw=%r final=%r",
                account_id,
                record.get("raw_display_diff_reason") or "unknown",
                raw_response,
                final_response,
            )
        if record.get("post_freeze_write_attempt"):
            logger.error(
                "[ai_response_unified.post_freeze_write] account_id=%s source=%s mutation_count=%s",
                account_id,
                record.get("display_mutation_source") or "unknown",
                record.get("display_mutation_count") or 0,
            )
