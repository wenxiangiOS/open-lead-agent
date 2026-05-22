"""运行时字段状态管理，记录已问、已收集、已跳过、已覆盖。Field state tracking."""

from dataclasses import dataclass
from typing import Any

from src.templates.config import ContactMethodConfig, FieldConfig, TemplateConfig

SKIP_PATTERNS = (
    "不方便",
    "不想说",
    "不说",
    "暂不透露",
    "保密",
    "先不说",
    "不留",
    "不提供",
)


@dataclass(frozen=True)
class FieldState:
    key: str
    status: str
    ask_count: int = 0
    value: Any = None

    @property
    def collected(self) -> bool:
        return self.status == "collected"

    @property
    def covered(self) -> bool:
        return self.status in {"collected", "covered", "skipped"}

    @property
    def skipped(self) -> bool:
        return self.status == "skipped"


class FieldStateService:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def build_states(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        skipped_fields: set[str] | None = None,
    ) -> dict[str, FieldState]:
        skipped_fields = skipped_fields or set()
        states: dict[str, FieldState] = {}
        for item in self._configured_items():
            states[item.key] = self._build_state(item, profile, ask_counts, skipped_fields)
        return states

    def infer_skipped_fields(
        self,
        *,
        user_message: str,
        target_key: str | None,
    ) -> set[str]:
        if not target_key:
            return set()
        normalized = user_message.strip().lower()
        if not normalized:
            return set()
        if any(pattern in normalized for pattern in SKIP_PATTERNS):
            return {target_key}
        return set()

    def is_covered(
        self,
        key: str,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        skipped_fields: set[str] | None = None,
    ) -> bool:
        state = self._build_state_by_key(key, profile, ask_counts, skipped_fields or set())
        return bool(state and state.covered)

    def _build_state(
        self,
        item: FieldConfig | ContactMethodConfig,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        skipped_fields: set[str],
    ) -> FieldState:
        value = profile.get(item.key)
        ask_count = ask_counts.get(item.key, 0)
        if value not in (None, ""):
            return FieldState(key=item.key, status="collected", ask_count=ask_count, value=value)
        if item.key in skipped_fields:
            return FieldState(key=item.key, status="skipped", ask_count=ask_count)
        if ask_count >= item.ask_limit > 0:
            return FieldState(key=item.key, status="covered", ask_count=ask_count)
        if ask_count > 0:
            return FieldState(key=item.key, status="asked", ask_count=ask_count)
        return FieldState(key=item.key, status="unasked", ask_count=ask_count)

    def _build_state_by_key(
        self,
        key: str,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        skipped_fields: set[str],
    ) -> FieldState | None:
        item = self._configured_item_map().get(key)
        if item is None:
            return None
        return self._build_state(item, profile, ask_counts, skipped_fields)

    def _configured_items(self) -> list[FieldConfig | ContactMethodConfig]:
        return [*self.template.fields, *self.template.contact.methods]

    def _configured_item_map(self) -> dict[str, FieldConfig | ContactMethodConfig]:
        return {item.key: item for item in self._configured_items()}
