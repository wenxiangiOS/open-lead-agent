from typing import Any

from src.templates.config import FieldConfig, TemplateConfig


class CollectionEngine:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def next_field(
        self, profile: dict[str, Any], ask_counts: dict[str, int] | None = None
    ) -> FieldConfig | None:
        return self.next_required_field(profile, ask_counts) or self.next_optional_field(
            profile, ask_counts
        )

    def next_required_field(
        self, profile: dict[str, Any], ask_counts: dict[str, int] | None = None
    ) -> FieldConfig | None:
        ordered = sorted(self.template.fields, key=lambda field: field.priority)
        for field in ordered:
            if field.required and self._should_ask(field, profile, ask_counts):
                return field
        return None

    def next_optional_field(
        self, profile: dict[str, Any], ask_counts: dict[str, int] | None = None
    ) -> FieldConfig | None:
        ordered = sorted(self.template.fields, key=lambda field: field.priority)
        for field in ordered:
            if not field.required and self._should_ask(field, profile, ask_counts):
                return field
        return None

    def extract_configured_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {field.key for field in self.template.fields}
        allowed.update(method.key for method in self.template.contact.methods)
        return {
            key: value
            for key, value in payload.items()
            if key in allowed and value not in (None, "")
        }

    def _should_ask(
        self, field: FieldConfig, profile: dict[str, Any], ask_counts: dict[str, int] | None
    ) -> bool:
        if profile.get(field.key):
            return False
        if ask_counts is None:
            return True
        return ask_counts.get(field.key, 0) < field.ask_limit
