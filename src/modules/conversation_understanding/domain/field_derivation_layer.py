from __future__ import annotations

import re
from datetime import datetime

from src.modules.conversation.domain.turn_understanding_models import (
    ResolvedFieldEvidence,
    TurnUnderstandingResult,
)
from src.modules.profile_collection.domain.extraction_service import ExtractionService


class FieldDerivationLayer:
    """Compatibility-only derivations after the persistence plan is built.

    This layer may enrich legacy projections such as ``resolved_slots`` or the
    compatibility persistence payload, but it is not part of the primary
    semantic decision path anymore.
    """

    _PARTNER_DERIVED_FIELDS = {
        "partner_pref_age",
        "partner_pref_location",
        "partner_pref_industry",
        "partner_pref_age_relation",
        "partner_pref_locality",
    }

    @staticmethod
    def _effective_resolved_slots(result: TurnUnderstandingResult) -> dict[str, str]:
        persistence_plan = getattr(result, "persistence_plan", None)
        resolved_slots = dict(result.resolved_slots or {})
        accepted_fields = getattr(persistence_plan, "accepted_fields", None) or []
        for field in accepted_fields:
            field_name = str(getattr(field, "field", "") or "").strip()
            if not field_name:
                continue
            resolved_slots[field_name] = str(getattr(field, "normalized_value", "") or "")
        return resolved_slots

    @staticmethod
    def _sync_derived_acceptance(result: TurnUnderstandingResult, field: str, value: str, evidence_text: str) -> None:
        persistence_plan = getattr(result, "persistence_plan", None)
        if persistence_plan is None:
            return
        from src.modules.conversation_understanding.domain.models import AcceptedField

        accepted_fields = list(getattr(persistence_plan, "accepted_fields", []) or [])
        if any(str(getattr(item, "field", "") or "").strip() == field for item in accepted_fields):
            return
        accepted_fields.append(
            AcceptedField(
                field=field,
                value=value,
                normalized_value=value,
                scope="partner",
                evidence_text=evidence_text,
                confidence=0.85,
                acceptance_reason="derived_from_partner_requirement",
                update_action="accept_as_new",
            )
        )
        persistence_plan.accepted_fields = accepted_fields

    def derive(self, *, result: TurnUnderstandingResult) -> TurnUnderstandingResult:
        derivations = dict(result.field_derivations or {})
        evidence = dict(result.resolved_field_evidence or {})
        resolved_slots = self._effective_resolved_slots(result)

        if "age_label" in resolved_slots:
            derivations["age_label"] = str(resolved_slots["age_label"]).strip()
        elif "age_label" in evidence:
            derivations["age_label"] = str(evidence["age_label"].value or "").strip()
        elif "age" in resolved_slots:
            derived = self._derive_age_label_from_age_evidence(evidence.get("age"))
            if derived:
                derivations["age_label"] = derived

        if "birth_year" not in derivations:
            derived_birth_year = self._derive_birth_year(
                age_label=derivations.get("age_label"),
                age=resolved_slots.get("age"),
            )
            if derived_birth_year:
                derivations["birth_year"] = derived_birth_year

        self._derive_partner_preference_subslots(
            result=result,
            resolved_slots=resolved_slots,
            evidence=evidence,
            derivations=derivations,
        )

        result.resolved_slots = resolved_slots
        result.resolved_field_evidence = evidence
        result.field_derivations = derivations
        return result

    def _derive_partner_preference_subslots(
        self,
        *,
        result: TurnUnderstandingResult,
        resolved_slots: dict[str, str],
        evidence: dict[str, ResolvedFieldEvidence],
        derivations: dict[str, str],
    ) -> None:
        requirement = str(resolved_slots.get("partner_requirement") or "").strip()
        if not requirement:
            return

        requirement_evidence = evidence.get("partner_requirement")
        if requirement_evidence is not None and requirement_evidence.scope not in {"partner", "mixed"}:
            return

        source_text = (
            str(requirement_evidence.source_text or "").strip()
            if requirement_evidence is not None
            else requirement
        ) or requirement
        source_span = (
            str(requirement_evidence.source_span or "").strip()
            if requirement_evidence is not None
            else requirement
        ) or requirement
        confidence = float(requirement_evidence.confidence or 0.85) if requirement_evidence is not None else 0.85

        for field, value in ExtractionService._extract_partner_preference_subslots(requirement).items():  # noqa: SLF001
            clean_value = str(value or "").strip()
            if not clean_value:
                continue
            if field in self._PARTNER_DERIVED_FIELDS and not str(resolved_slots.get(field) or "").strip():
                resolved_slots[field] = clean_value
            derivations[field] = clean_value
            self._sync_derived_acceptance(result, field, clean_value, source_text)
            if field not in evidence:
                evidence[field] = ResolvedFieldEvidence(
                    field=field,
                    value=clean_value,
                    scope="partner",
                    source_span=source_span,
                    source_text=source_text,
                    confidence=confidence,
                    source_type="derived",
                    derived_from="partner_requirement",
                )

    @staticmethod
    def _derive_age_label_from_age_evidence(evidence: ResolvedFieldEvidence | None) -> str:
        if evidence is None or evidence.scope != "self":
            return ""
        source_span = str(evidence.source_span or "").strip()
        if re.fullmatch(r"(?:19\d{2}|20\d{2})年", source_span):
            return source_span
        if re.fullmatch(r"\d{2}年", source_span):
            return source_span
        if re.fullmatch(r"\d{2}后", source_span):
            return source_span
        return ""

    @staticmethod
    def _derive_birth_year(*, age_label: str | None, age: str | int | None) -> str:
        label = str(age_label or "").strip()
        if re.fullmatch(r"(19\d{2}|20\d{2})年", label):
            return label[:-1]
        match = re.fullmatch(r"(\d{2})年", label)
        if match:
            suffix = int(match.group(1))
            current_suffix = datetime.now().year % 100
            return str(2000 + suffix if suffix <= current_suffix else 1900 + suffix)
        match = re.fullmatch(r"(\d{2})后", label)
        if match:
            suffix = int(match.group(1))
            century = 2000 if suffix <= datetime.now().year % 100 else 1900
            return str(century + suffix)

        age_value = str(age or "").strip()
        if age_value.isdigit():
            return str(datetime.now().year - int(age_value))
        return ""
