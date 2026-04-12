from __future__ import annotations

import logging
from typing import Any, Dict

from src.models.user_profile import UserProfile
from src.models.user_state import UserState
from src.services.queue.turn_draft_models import TurnMutationSet

logger = logging.getLogger(__name__)


class TurnCommitService:
    """Apply deferred per-turn business mutations exactly once."""

    def __init__(self, user_service: Any, queue_store: Any) -> None:
        self.user_service = user_service
        self.queue_store = queue_store

    async def commit_turn(self, turn_id: str, account_id: str, mutation_set: TurnMutationSet) -> bool:
        if not turn_id:
            return False

        if await self.queue_store.is_turn_committed(turn_id):
            return True

        try:
            if mutation_set.profile_dirty and mutation_set.profile:
                profile = UserProfile.from_dict(dict(mutation_set.profile))
                await self.user_service.save_user_profile(account_id, profile)

            if mutation_set.state_dirty and mutation_set.state:
                state = UserState.from_dict(dict(mutation_set.state), user_id=account_id)
                await self.user_service.save_user_state(account_id, state)

            await self.queue_store.mark_turn_committed(turn_id)
            return True
        except Exception:
            logger.exception(
                "[mq.commit] commit failed",
                extra={"turn_id": turn_id, "account_id": account_id},
            )
            return False

    @staticmethod
    def from_payload(payload: Dict[str, Any] | None) -> TurnMutationSet:
        data = payload or {}
        if isinstance(data, TurnMutationSet):
            return data
        return TurnMutationSet(
            profile_dirty=bool(data.get("profile_dirty", False)),
            profile=data.get("profile"),
            state_dirty=bool(data.get("state_dirty", False)),
            state=data.get("state"),
            metadata=dict(data.get("metadata") or {}),
        )
