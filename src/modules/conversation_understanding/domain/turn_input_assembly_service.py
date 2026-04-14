from __future__ import annotations

from typing import Any

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput
from src.modules.conversation_understanding.domain.models import TurnInputSnapshot


class TurnInputAssemblyService:
    """Build the single structured snapshot consumed by the semantic pipeline."""

    def build_snapshot(self, turn_input: TurnUnderstandingInput) -> TurnInputSnapshot:
        profile = getattr(turn_input, "user_profile", None)
        prompt_state = getattr(profile, "last_question_state", None) if profile is not None else None
        semantic_summary = getattr(profile, "last_semantic_summary", None) if profile is not None else None
        return TurnInputSnapshot(
            user_message=turn_input.user_message,
            last_response=turn_input.last_response,
            message_count=turn_input.message_count,
            conversation_context=dict(turn_input.conversation_context or {}),
            in_contact_flow=bool(turn_input.in_contact_flow),
            pending_confirmation_field=turn_input.pending_confirmation_field,
            prompt_state=dict(prompt_state or {}) if isinstance(prompt_state, dict) else {},
            prior_semantic_summary=dict(semantic_summary or {}) if isinstance(semantic_summary, dict) else {},
            user_profile=profile,
        )
