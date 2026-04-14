from __future__ import annotations

from src.modules.conversation.domain.turn_understanding_models import ResolvedFieldEvidence
from src.modules.conversation_understanding.domain.models import TurnPersistencePlan


class PersistencePlanToResolvedSlotsAdapter:
    """Project accepted fields back into legacy slot structures."""

    def project_slots(self, *, plan: TurnPersistencePlan) -> dict[str, str]:
        projected_fields = self._projected_fields(plan)
        return {
            field.field: str(field.normalized_value)
            for field in projected_fields
            if field.scope in {"self", "contact", "partner"}
        }

    def project_evidence(
        self,
        *,
        plan: TurnPersistencePlan,
        fallback_evidence: dict[str, ResolvedFieldEvidence] | None = None,
    ) -> dict[str, ResolvedFieldEvidence]:
        observation_map = {
            (obs.field, str(obs.normalized_value)): obs
            for obs in plan.observation_log
        }
        fallback_evidence = dict(fallback_evidence or {})
        evidence: dict[str, ResolvedFieldEvidence] = {}
        for field in self._projected_fields(plan):
            observation = observation_map.get((field.field, str(field.normalized_value)))
            prior = fallback_evidence.get(field.field)
            source_span = observation.evidence_span if observation is not None else field.evidence_text
            source_text = observation.evidence_text if observation is not None else field.evidence_text
            state = str(getattr(field, "persistence_state", "committed") or "committed").strip()
            evidence[field.field] = ResolvedFieldEvidence(
                field=field.field,
                value=str(field.normalized_value),
                scope=field.scope,
                source_span=source_span or getattr(prior, "source_span", "") or "",
                source_text=source_text or getattr(prior, "source_text", ""),
                confidence=float(field.confidence or 0.0),
                source_type=getattr(prior, "source_type", "") or (
                    "persistence_plan_projection"
                    if state == "committed"
                    else "persistence_plan_provisional_projection"
                ),
                derived_from=getattr(prior, "derived_from", None),
            )
        return evidence

    @staticmethod
    def _projected_fields(plan: TurnPersistencePlan):
        accepted = list(getattr(plan, "accepted_fields", []) or [])
        provisional = list(getattr(plan, "provisional_fields", []) or [])
        projected_map: dict[str, object] = {}
        for field in accepted + provisional:
            field_name = str(getattr(field, "field", "") or "").strip()
            if not field_name:
                continue
            existing = projected_map.get(field_name)
            if existing is None:
                projected_map[field_name] = field
                continue
            # partner_requirement 投影优先保留信息量更丰富的表达，避免结构化 compose 裁掉尾巴后影响展示/追问体验。
            if field_name == "partner_requirement":
                existing_text = str(getattr(existing, "normalized_value", "") or "")
                candidate_text = str(getattr(field, "normalized_value", "") or "")
                if len(candidate_text) > len(existing_text):
                    projected_map[field_name] = field
        return list(projected_map.values())
