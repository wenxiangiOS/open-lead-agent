from __future__ import annotations

import re
from datetime import datetime

from src.modules.conversation.domain.turn_understanding_models import (
    ResolvedFieldEvidence,
    TurnUnderstandingResult,
)


class FieldDerivationLayer:
    """Derive secondary fields only from resolved evidence, never by rescanning the full message."""

    def derive(self, *, result: TurnUnderstandingResult) -> TurnUnderstandingResult:
        derivations = dict(result.field_derivations or {})
        evidence = dict(result.resolved_field_evidence or {})

        if "age_label" in result.resolved_slots:
            derivations["age_label"] = str(result.resolved_slots["age_label"]).strip()
        elif "age_label" in evidence:
            derivations["age_label"] = str(evidence["age_label"].value or "").strip()
        elif "age" in result.resolved_slots:
            derived = self._derive_age_label_from_age_evidence(evidence.get("age"))
            if derived:
                derivations["age_label"] = derived

        if "birth_year" not in derivations:
            derived_birth_year = self._derive_birth_year(
                age_label=derivations.get("age_label"),
                age=result.resolved_slots.get("age"),
            )
            if derived_birth_year:
                derivations["birth_year"] = derived_birth_year

        result.field_derivations = derivations
        return result

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
