from collections import defaultdict
from copy import deepcopy
from typing import Any


class MemoryStore:
    def __init__(self):
        self._profiles: dict[str, dict[str, Any]] = defaultdict(dict)
        self._history: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._ask_counts: dict[str, dict[str, int]] = defaultdict(dict)

    def get_profile(self, account_id: str) -> dict[str, Any]:
        return deepcopy(self._profiles[account_id])

    def update_profile(self, account_id: str, values: dict[str, Any]) -> dict[str, Any]:
        clean_values = {key: value for key, value in values.items() if value not in (None, "")}
        self._profiles[account_id].update(clean_values)
        return self.get_profile(account_id)

    def append_message(self, account_id: str, role: str, content: str) -> None:
        self._history[account_id].append({"role": role, "content": content})

    def get_history(self, account_id: str) -> list[dict[str, str]]:
        return deepcopy(self._history[account_id])

    def get_ask_counts(self, account_id: str) -> dict[str, int]:
        return deepcopy(self._ask_counts[account_id])

    def increment_ask_count(self, account_id: str, field_key: str) -> None:
        current = self._ask_counts[account_id].get(field_key, 0)
        self._ask_counts[account_id][field_key] = current + 1
