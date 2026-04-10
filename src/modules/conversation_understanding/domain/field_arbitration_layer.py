from __future__ import annotations

from src.modules.conversation.domain.turn_understanding_models import ResolvedFieldEvidence, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.models import FieldPermissionResult


class FieldArbitrationLayer:
    """Rebuild final resolved slots from filtered candidates.

    This makes the unified pipeline the final owner of resolved_slots instead of
    passively inheriting them from the legacy deterministic extractor.
    """

    def arbitrate(
        self,
        *,
        result: TurnUnderstandingResult,
        permission_result: FieldPermissionResult,
    ) -> TurnUnderstandingResult:
        candidates = dict(result.slot_candidates or {})
        if not candidates:
            result.resolved_slots = {}
            return result

        priority_fields = [field for field in (permission_result.priority_fields or []) if field in candidates]
        ordered_fields = priority_fields + [field for field in candidates.keys() if field not in priority_fields]

        rebuilt: dict[str, str] = {}
        rebuilt_evidence: dict[str, ResolvedFieldEvidence] = {}
        for field in ordered_fields:
            candidate = candidates.get(field)
            if candidate is None:
                continue
            value = str(getattr(candidate, "value", "") or "").strip()
            if not value:
                continue
            rebuilt[field] = value
            rebuilt_evidence[field] = ResolvedFieldEvidence(
                field=field,
                value=value,
                scope=str(getattr(candidate, "scope", "") or "mixed").strip() or "mixed",
                source_span=str(getattr(candidate, "source_span", "") or value).strip() or value,
                source_text=str(getattr(candidate, "source_text", "") or "").strip(),
                confidence=float(getattr(candidate, "confidence", 0.0) or 0.0),
                source_type=str(getattr(candidate, "source", "") or "rule").strip() or "rule",
            )

        result.resolved_slots = rebuilt
        result.resolved_field_evidence = rebuilt_evidence
        return result
