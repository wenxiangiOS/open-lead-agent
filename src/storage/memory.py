"""内存版对话状态存储，适合本地开发和测试。In-memory state store."""

from collections import defaultdict
from copy import deepcopy
from typing import Any

from src.collection.confirmation import PendingConfirmation


class MemoryStore:
    def __init__(self):
        self._profiles: dict[str, dict[str, Any]] = defaultdict(dict)
        self._history: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._ask_counts: dict[str, dict[str, int]] = defaultdict(dict)
        self._skipped_fields: dict[str, set[str]] = defaultdict(set)
        self._last_targets: dict[str, str | None] = {}
        self._pending_confirmations: dict[str, list[PendingConfirmation]] = defaultdict(list)

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

    def get_skipped_fields(self, account_id: str) -> set[str]:
        return set(self._skipped_fields[account_id])

    def mark_skipped_fields(self, account_id: str, field_keys: set[str]) -> None:
        self._skipped_fields[account_id].update(field_keys)

    def get_last_target(self, account_id: str) -> str | None:
        return self._last_targets.get(account_id)

    def set_last_target(self, account_id: str, field_key: str | None) -> None:
        self._last_targets[account_id] = field_key

    def get_pending_confirmation(self, account_id: str) -> PendingConfirmation | None:
        queue = self._pending_confirmations.get(account_id) or []
        if not queue:
            return None
        return queue[0]

    def get_pending_confirmations(self, account_id: str) -> list[PendingConfirmation]:
        return list(self._pending_confirmations.get(account_id) or [])

    def set_pending_confirmation(
        self,
        account_id: str,
        task: PendingConfirmation | None,
    ) -> None:
        if task is None:
            self._pending_confirmations.pop(account_id, None)
            return
        self._pending_confirmations[account_id] = [task]

    def add_pending_confirmations(
        self,
        account_id: str,
        tasks: list[PendingConfirmation],
    ) -> None:
        if not tasks:
            return
        existing_keys = {task.field_key for task in self._pending_confirmations[account_id]}
        for task in tasks:
            if task.field_key not in existing_keys:
                self._pending_confirmations[account_id].append(task)
                existing_keys.add(task.field_key)

    def clear_current_pending_confirmation(self, account_id: str) -> None:
        queue = self._pending_confirmations.get(account_id)
        if not queue:
            return
        queue.pop(0)
        if not queue:
            self._pending_confirmations.pop(account_id, None)
