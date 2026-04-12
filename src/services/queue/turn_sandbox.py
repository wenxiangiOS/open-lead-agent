from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from src.services.queue.turn_draft_models import TurnMutationSet


class TurnSandbox:
    """Per-turn sandbox that defers user-state writes until final commit."""

    def __init__(self, user_service: Any, account_id: str) -> None:
        self.user_service = user_service
        self.account_id = account_id
        self._token: Optional[Any] = None

    async def __aenter__(self) -> "TurnSandbox":
        begin = getattr(self.user_service, "begin_turn_sandbox", None)
        if callable(begin):
            self._token = begin(self.account_id)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            rollback = getattr(self.user_service, "rollback_turn_sandbox", None)
            if callable(rollback):
                rollback(self._token)
            return False

        end = getattr(self.user_service, "end_turn_sandbox", None)
        if callable(end):
            end(self._token)
        return False

    def collect_mutation_set(self) -> TurnMutationSet:
        collect = getattr(self.user_service, "collect_turn_mutation_set", None)
        if not callable(collect):
            return TurnMutationSet()

        data = collect(self._token) or {}
        if isinstance(data, TurnMutationSet):
            return data

        return TurnMutationSet(
            profile_dirty=bool(data.get("profile_dirty", False)),
            profile=data.get("profile"),
            state_dirty=bool(data.get("state_dirty", False)),
            state=data.get("state"),
            metadata=dict(data.get("metadata") or {}),
        )

    @staticmethod
    def serialize_mutation_set(mutation_set: TurnMutationSet) -> Dict[str, Any]:
        return asdict(mutation_set)
