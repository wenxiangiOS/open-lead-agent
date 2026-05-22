"""可配置收尾策略，处理联系方式完成和无下一步动作。Closing policy."""

from typing import Any

from src.collection.state import FieldState
from src.templates.config import TemplateConfig


class ClosingDecision:
    def __init__(self, reason: str, message: str):
        self.reason = reason
        self.message = message


class ClosingPolicy:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def evaluate(
        self,
        *,
        profile: dict[str, Any],
        field_states: dict[str, FieldState] | None,
        collected_this_turn: dict[str, Any],
        contact_allowed: bool,
        no_next_action: bool = False,
    ) -> ClosingDecision | None:
        if not self.template.closing.enabled:
            return None

        trigger = self.template.closing.trigger
        if (
            trigger.after_contact_collected
            and self._contact_collected_this_turn(collected_this_turn)
            and self._core_profile_covered(profile, field_states)
        ):
            return ClosingDecision("contact_collected", self.template.closing.message)

        if (
            trigger.after_contact_covered
            and contact_allowed
            and self._all_contact_methods_covered(profile, field_states)
        ):
            return ClosingDecision("contact_covered", self.template.closing.message)

        if trigger.when_no_next_action and no_next_action:
            return ClosingDecision("no_next_action", self.template.closing.message)

        return None

    def _contact_collected_this_turn(self, collected_this_turn: dict[str, Any]) -> bool:
        contact_keys = {method.key for method in self.template.contact.methods}
        return any(key in collected_this_turn for key in contact_keys)

    def _all_contact_methods_covered(
        self,
        profile: dict[str, Any],
        field_states: dict[str, FieldState] | None,
    ) -> bool:
        if not self.template.contact.methods:
            return False
        for method in self.template.contact.methods:
            if profile.get(method.key):
                continue
            if field_states is None:
                return False
            state = field_states.get(method.key)
            if state is None or not state.covered:
                return False
        return True

    def _core_profile_covered(
        self,
        profile: dict[str, Any],
        field_states: dict[str, FieldState] | None,
    ) -> bool:
        required_keys = self.template.contact.trigger.required_fields or [
            field.key for field in self.template.fields if field.required
        ]
        if not required_keys:
            return True
        for key in required_keys:
            if profile.get(key):
                continue
            if field_states is None:
                return False
            state = field_states.get(key)
            if state is None or not state.covered:
                return False
        return True
