"""字段接受与提交计划。

这一层把字段观察转换成 accepted/provisional/pending/rejected，
避免“LLM 说提取到了”就直接污染档案。
"""

from typing import Any

from src.templates.config import ContactMethodConfig, FieldConfig, TemplateConfig
from src.understanding.context import configured_item_map
from src.understanding.models import FieldObservation, PersistencePlan, TurnSemanticFrame
from src.understanding.normalization import FieldNormalizer
from src.understanding.validation import FieldValueValidator


class FieldAcceptanceService:
    _TRUSTED_SOURCES = {"llm", "ai", "model", "ai_structured_extraction"}
    _UNTRUSTED_HIGH_RISK_SOURCES = {"fallback", "regex", "rule", "heuristic"}

    def __init__(self, template: TemplateConfig):
        self.template = template
        self.normalizer = FieldNormalizer()
        self.validator = FieldValueValidator()

    def build_plan(
        self,
        frame: TurnSemanticFrame,
        profile: dict[str, Any],
    ) -> PersistencePlan:
        configured = configured_item_map(self.template)
        accepted: dict[str, Any] = {}
        provisional: dict[str, Any] = {}
        pending: dict[str, Any] = {}
        rejected: dict[str, Any] = {}
        observation_log: list[FieldObservation] = []

        for observation in frame.observations:
            config = configured.get(observation.field)
            if config is None:
                rejected[observation.field] = observation.value
                observation_log.append(
                    self._replace(observation, reason="not_configured_or_not_extractable")
                )
                continue
            if self._is_empty(observation.value):
                rejected[observation.field] = observation.value
                observation_log.append(self._replace(observation, reason="empty_value"))
                continue

            normalized = self.normalizer.normalize(config, observation.value)
            if normalized is None or self._is_empty(normalized):
                rejected[observation.field] = observation.value
                observation_log.append(self._replace(observation, reason="invalid_format"))
                continue

            existing_value = profile.get(observation.field)
            if existing_value not in (None, ""):
                if self._same_value(existing_value, normalized):
                    rejected[observation.field] = normalized
                    observation_log.append(
                        self._replace(
                            observation,
                            normalized_value=normalized,
                            reason="already_collected",
                        )
                    )
                else:
                    pending[observation.field] = {
                        "current": existing_value,
                        "new": normalized,
                    }
                    observation_log.append(
                        self._replace(
                            observation,
                            normalized_value=normalized,
                            reason="conflict_with_existing_value",
                        )
                    )
                continue

            status, reason = self._classify_new_value(config, observation)
            committed_observation = self._replace(
                observation,
                normalized_value=normalized,
                reason=reason,
            )
            observation_log.append(committed_observation)
            if status == "pending":
                pending[observation.field] = normalized
            elif status == "provisional":
                provisional[observation.field] = normalized
            else:
                accepted[observation.field] = normalized

        return PersistencePlan(
            accepted_fields=accepted,
            provisional_fields=provisional,
            pending_fields=pending,
            rejected_fields=rejected,
            observation_log=observation_log,
        )

    def _classify_new_value(
        self,
        config: FieldConfig | ContactMethodConfig,
        observation: FieldObservation,
    ) -> tuple[str, str]:
        """Return persistence bucket and reason for a new normalized value."""
        if observation.write_mode != "direct_write":
            return "pending", "soft_confirm"

        if observation.confidence < self.validator.min_confidence(config):
            if self._requires_confirmation_on_low_confidence(config):
                return "pending", "low_confidence_requires_confirmation"
            return "provisional", "low_confidence_stage_as_provisional"

        if self._is_untrusted_high_risk_source(config, observation):
            return "pending", "high_risk_untrusted_source"

        return "accepted", self._acceptance_reason(config, observation)

    def _requires_confirmation_on_low_confidence(
        self,
        config: FieldConfig | ContactMethodConfig,
    ) -> bool:
        if isinstance(config, ContactMethodConfig):
            return True
        if config.required:
            return True
        return self.validator.is_high_risk(config)

    def _is_untrusted_high_risk_source(
        self,
        config: FieldConfig | ContactMethodConfig,
        observation: FieldObservation,
    ) -> bool:
        if not self.validator.is_high_risk(config):
            return False
        source = observation.source.strip().lower()
        if source in self._TRUSTED_SOURCES:
            return False
        if source in self._UNTRUSTED_HIGH_RISK_SOURCES:
            return True
        return False

    def _needs_confirmation(
        self,
        config: FieldConfig | ContactMethodConfig,
        observation: FieldObservation,
    ) -> bool:
        return (
            observation.write_mode == "soft_confirm"
            or observation.confidence < self.validator.min_confidence(config)
        )

    def _acceptance_reason(
        self,
        config: FieldConfig | ContactMethodConfig,
        observation: FieldObservation,
    ) -> str:
        if self._needs_confirmation(config, observation):
            return "pending_confirmation"
        return "accepted"

    def _same_value(self, left: Any, right: Any) -> bool:
        return str(left).strip().lower() == str(right).strip().lower()

    def _replace(
        self,
        observation: FieldObservation,
        *,
        normalized_value: Any = None,
        reason: str,
    ) -> FieldObservation:
        return FieldObservation(
            field=observation.field,
            value=observation.value,
            normalized_value=normalized_value
            if normalized_value is not None
            else observation.normalized_value,
            scope=observation.scope,
            owner=observation.owner,
            evidence_text=observation.evidence_text,
            confidence=observation.confidence,
            write_mode=observation.write_mode,
            source=observation.source,
            reason=reason,
        )

    def _is_empty(self, value: Any) -> bool:
        return value is None or value == "" or value == []
