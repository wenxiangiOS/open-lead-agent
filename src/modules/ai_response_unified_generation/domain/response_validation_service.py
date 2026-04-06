from __future__ import annotations

import re

from .models import AIResponseValidationResult


class ResponseValidationService:
    """Validate only. Never rewrite user-visible text."""

    _DEBUG_PATTERNS = (
        r"traceback \(most recent call last\)",
        r"\bexception\b",
        r"\berror:\b",
        r"<html[\s>]",
        r"internal server error",
        r"bad gateway",
        r"debug[:\]]",
    )

    def validate(self, *, raw_ai_response: str, infra_fail: bool = False, infra_fail_reason: str = "") -> AIResponseValidationResult:
        text = str(raw_ai_response or "").strip()
        if infra_fail:
            return AIResponseValidationResult(
                delivery_status="fallback_required",
                should_fallback=True,
                fallback_reason=infra_fail_reason or "ai_infra_fail",
            )
        if not text:
            return AIResponseValidationResult(
                delivery_status="fallback_required",
                should_fallback=True,
                fallback_reason="ai_empty_response",
            )
        lowered = text.lower()
        for pattern in self._DEBUG_PATTERNS:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return AIResponseValidationResult(
                    delivery_status="fallback_required",
                    violations=["invalid_ai_payload"],
                    should_fallback=True,
                    fallback_reason="invalid_ai_payload",
                )
        warnings: list[str] = []
        if len(text) < 2:
            warnings.append("too_short")
        return AIResponseValidationResult(
            delivery_status="warning" if warnings else "deliverable",
            warnings=warnings,
        )
