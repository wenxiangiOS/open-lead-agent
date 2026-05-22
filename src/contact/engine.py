"""按模板配置和询问次数选择下一个联系方式字段。Contact method selection."""

from typing import Any

from src.templates.config import ContactMethodConfig, TemplateConfig


class ContactEngine:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def next_contact_method(
        self, profile: dict[str, Any], ask_counts: dict[str, int] | None = None
    ) -> ContactMethodConfig | None:
        if not self.template.contact.enabled:
            return None
        for method in self.template.contact.methods:
            if method.required and self._should_ask(method, profile, ask_counts):
                return method
        for method in self.template.contact.methods:
            if self._should_ask(method, profile, ask_counts):
                return method
        return None

    def _should_ask(
        self,
        method: ContactMethodConfig,
        profile: dict[str, Any],
        ask_counts: dict[str, int] | None,
    ) -> bool:
        if profile.get(method.key):
            return False
        if ask_counts is None:
            return True
        return ask_counts.get(method.key, 0) < method.ask_limit
