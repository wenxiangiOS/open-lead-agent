"""判断资料是否足够进入联系方式收集。Contact collection gate."""

from typing import Any

from src.collection.state import FieldState
from src.templates.config import FieldConfig, TemplateConfig


class ContactGate:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def allows_contact(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None = None,
    ) -> bool:
        if not self.template.contact.enabled:
            return False

        trigger = self.template.contact.trigger
        if trigger.mode != "coverage_gate":
            return self._legacy_required_fields_done(profile, ask_counts, field_states)

        required_keys = trigger.required_fields or [
            field.key for field in self.template.fields if field.required
        ]
        optional_keys = trigger.optional_fields
        required_collected_count = len([key for key in required_keys if profile.get(key)])
        if (
            trigger.min_required_collected > 0
            and required_collected_count < trigger.min_required_collected
        ):
            return False
        if trigger.require_all_core_covered:
            core_covered = all(
                self._field_is_covered(key, profile, ask_counts, field_states)
                for key in required_keys
            )
            if not core_covered:
                return False
        if trigger.require_all_optional_covered:
            optional_covered = all(
                self._field_is_covered(key, profile, ask_counts, field_states)
                for key in optional_keys
            )
            if not optional_covered:
                return False
        if (
            trigger.min_required_collected <= 0
            and not trigger.require_all_core_covered
            and not trigger.require_all_optional_covered
        ):
            return all(
                self._field_is_covered(key, profile, ask_counts, field_states)
                for key in required_keys
            )
        return True

    def explain(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None = None,
    ) -> dict[str, Any]:
        """Return a debug-friendly explanation for contact gate state."""
        trigger = self.template.contact.trigger
        required_keys = trigger.required_fields or [
            field.key for field in self.template.fields if field.required
        ]
        optional_keys = trigger.optional_fields
        collected = [key for key in required_keys if profile.get(key)]
        covered = [
            key
            for key in required_keys
            if self._field_is_covered(key, profile, ask_counts, field_states)
        ]
        optional_collected = [key for key in optional_keys if profile.get(key)]
        optional_covered = [
            key
            for key in optional_keys
            if self._field_is_covered(key, profile, ask_counts, field_states)
        ]
        missing = [key for key in required_keys if key not in collected]
        uncovered = [key for key in required_keys if key not in covered]
        optional_missing = [key for key in optional_keys if key not in optional_collected]
        optional_uncovered = [key for key in optional_keys if key not in optional_covered]
        gate_keys = [*required_keys, *optional_keys]
        return {
            "enabled": self.template.contact.enabled,
            "mode": trigger.mode,
            "allowed": self.allows_contact(profile, ask_counts, field_states),
            "required_fields": required_keys,
            "optional_fields": optional_keys,
            "gate_fields": gate_keys,
            "collected": collected,
            "covered": covered,
            "missing": missing,
            "uncovered": uncovered,
            "optional_collected": optional_collected,
            "optional_covered": optional_covered,
            "optional_missing": optional_missing,
            "optional_uncovered": optional_uncovered,
            "min_required_collected": trigger.min_required_collected,
            "require_all_core_covered": trigger.require_all_core_covered,
            "require_all_optional_covered": trigger.require_all_optional_covered,
            "ask_counts": {key: ask_counts.get(key, 0) for key in gate_keys},
        }

    def _legacy_required_fields_done(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None,
    ) -> bool:
        if self.template.contact.ask_after_required_fields:
            return all(
                self._field_is_covered(field.key, profile, ask_counts, field_states)
                for field in self.template.fields
                if field.required
            )
        return False

    def _field_is_covered(
        self,
        key: str,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None,
    ) -> bool:
        if field_states is not None and key in field_states:
            return field_states[key].covered
        if profile.get(key):
            return True
        field = self._field_by_key(key)
        if field is None:
            return False
        return ask_counts.get(key, 0) >= field.ask_limit

    def _field_by_key(self, key: str) -> FieldConfig | None:
        for field in self.template.fields:
            if field.key == key:
                return field
        return None
