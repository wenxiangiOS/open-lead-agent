from collections import defaultdict
from copy import deepcopy
from typing import Any


class MemoryStore:
    def __init__(self):
        self._profiles: dict[str, dict[str, Any]] = defaultdict(dict)
        self._history: dict[str, list[dict[str, str]]] = defaultdict(list)

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
