from typing import Any

from src.templates.config import ContactMethodConfig, TemplateConfig


class ContactEngine:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def next_contact_method(self, profile: dict[str, Any]) -> ContactMethodConfig | None:
        if not self.template.contact.enabled:
            return None
        for method in self.template.contact.methods:
            if method.required and not profile.get(method.key):
                return method
        for method in self.template.contact.methods:
            if not profile.get(method.key):
                return method
        return None
