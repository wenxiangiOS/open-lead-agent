from __future__ import annotations

import re

from src.modules.conversation_understanding.domain.models import FieldObservation, TurnSemanticFrame


class SemanticNormalizationService:
    """Normalize shorthand expressions without changing field ownership."""

    def normalize(self, frame: TurnSemanticFrame) -> TurnSemanticFrame:
        observations = [self._normalize_observation(obs) for obs in frame.field_observations]
        return TurnSemanticFrame(
            version=frame.version,
            source=frame.source,
            primary_domain=frame.primary_domain,
            acts=list(frame.acts),
            user_questions=list(frame.user_questions),
            field_observations=observations,
            risk_flags=list(frame.risk_flags),
            boundaries=list(frame.boundaries),
            notes=list(frame.notes),
            confidence=frame.confidence,
        )

    def _normalize_observation(self, observation: FieldObservation) -> FieldObservation:
        field_name = observation.field
        normalized_value = observation.normalized_value
        raw_value = observation.raw_value
        unit = observation.unit

        if field_name in {"height", "weight"}:
            compact = str(raw_value or observation.evidence_text or "").strip()
            shorthand_match = re.fullmatch(r"(\d{3})\s*/\s*(\d{2,3})", compact)
            if shorthand_match:
                if field_name == "height":
                    normalized_value = int(shorthand_match.group(1))
                    raw_value = compact
                    unit = unit or "cm"
                elif field_name == "weight":
                    normalized_value = int(shorthand_match.group(2))
                    raw_value = compact
                    unit = unit or "jin"

        return FieldObservation(
            field=observation.field,
            value=observation.value,
            normalized_value=normalized_value,
            scope=observation.scope,
            owner=observation.owner,
            evidence_text=observation.evidence_text,
            evidence_span=observation.evidence_span,
            confidence=observation.confidence,
            write_mode=observation.write_mode,
            source=observation.source,
            raw_value=raw_value,
            unit=unit,
            relation=observation.relation,
            conflict_hint=observation.conflict_hint,
        )
