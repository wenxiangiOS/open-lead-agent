from __future__ import annotations

from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    FieldObservation,
    PendingField,
    PromptState,
    RejectedField,
    TurnPersistencePlan,
    TurnSemanticFrame,
)


class PersistencePlanService:
    """Build the single persistence plan consumed by downstream orchestration."""

    def build_plan(
        self,
        *,
        frame: TurnSemanticFrame,
        accepted_fields: list[AcceptedField],
        provisional_fields: list[AcceptedField],
        pending_fields: list[PendingField],
        rejected_fields: list[RejectedField],
        expected_profile_version: int | None = None,
        expected_profile_updated_at: str | None = None,
    ) -> TurnPersistencePlan:
        prompt_state = self._build_prompt_state(
            frame=frame,
            pending_fields=pending_fields,
            provisional_fields=provisional_fields,
        )
        resume_fields = list(pending_fields) + list(provisional_fields)
        next_resume_target = resume_fields[0].field if resume_fields else None
        return TurnPersistencePlan(
            accepted_fields=list(accepted_fields),
            provisional_fields=list(provisional_fields),
            pending_fields=list(pending_fields),
            rejected_fields=list(rejected_fields),
            observation_log=list(frame.field_observations),
            update_prompt_state=prompt_state,
            next_resume_target=next_resume_target,
            expected_profile_version=expected_profile_version,
            expected_profile_updated_at=expected_profile_updated_at,
        )

    @staticmethod
    def _build_prompt_state(
        *,
        frame: TurnSemanticFrame,
        pending_fields: list[PendingField],
        provisional_fields: list[AcceptedField],
    ) -> PromptState:
        main_target = pending_fields[0].field if pending_fields else (provisional_fields[0].field if provisional_fields else None)
        expected_scopes = sorted({obs.scope for obs in frame.field_observations if obs.scope})
        return PromptState(
            prompt_type=frame.primary_domain,
            main_target=main_target,
            side_targets=[],
            expected_scopes=expected_scopes,
            allows_mixed_answer=True,
            pending_confirmations=[field.field for field in pending_fields]
            + [field.field for field in provisional_fields],
        )
