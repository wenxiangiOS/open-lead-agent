from typing import Any

from src.templates.config import FieldConfig, TemplateConfig


class CollectionEngine:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def next_field(self, profile: dict[str, Any]) -> FieldConfig | None:
        ordered = sorted(self.template.fields, key=lambda field: field.priority)
        for field in ordered:
            if field.required and not profile.get(field.key):
                return field
        for field in ordered:
            if not field.required and not profile.get(field.key):
                return field
        return None

    def extract_configured_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {field.key for field in self.template.fields}
        allowed.update(method.key for method in self.template.contact.methods)
        return {key: value for key, value in payload.items() if key in allowed and value not in (None, "")}
