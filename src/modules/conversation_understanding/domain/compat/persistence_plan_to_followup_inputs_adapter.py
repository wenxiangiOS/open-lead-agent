from __future__ import annotations

from src.modules.conversation_understanding.domain.models import TurnPersistencePlan


class PersistencePlanToFollowupInputsAdapter:
    """Project persistence outputs into lightweight followup inputs for legacy consumers."""

    def project(self, *, plan: TurnPersistencePlan) -> dict[str, object]:
        prompt_state = plan.update_prompt_state
        return {
            "main_target": getattr(prompt_state, "main_target", None),
            "pending_confirmations": list(getattr(prompt_state, "pending_confirmations", []) or []),
            "next_resume_target": plan.next_resume_target,
            "provisional_fields": [
                str(getattr(field, "field", "") or "").strip()
                for field in list(getattr(plan, "provisional_fields", []) or [])
                if str(getattr(field, "field", "") or "").strip()
            ],
        }
