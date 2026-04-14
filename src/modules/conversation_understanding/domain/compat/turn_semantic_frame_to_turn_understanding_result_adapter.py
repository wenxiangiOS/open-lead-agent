from __future__ import annotations

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.modules.conversation_understanding.domain.models import TurnSemanticFrame


class TurnSemanticFrameToTurnUnderstandingResultAdapter:
    """Compatibility projection only.

    Migration-stage adapter that attaches the new semantic frame to the legacy
    result object without reinterpreting the raw message.
    """

    def project(
        self,
        *,
        frame: TurnSemanticFrame,
        fallback_result: TurnUnderstandingResult,
    ) -> TurnUnderstandingResult:
        projected_turn_type, projected_subtype = self._project_turn_type(
            frame=frame,
            fallback_result=fallback_result,
        )
        fallback_result.primary_turn_type = projected_turn_type
        fallback_result.subtype = projected_subtype
        if getattr(frame, "confidence", 0.0):
            fallback_result.confidence = float(getattr(frame, "confidence", 0.0) or fallback_result.confidence or 0.0)
        setattr(fallback_result, "semantic_frame", frame)
        return fallback_result

    @staticmethod
    def _project_turn_type(
        *,
        frame: TurnSemanticFrame,
        fallback_result: TurnUnderstandingResult,
    ) -> tuple[str, str | None]:
        primary_domain = str(getattr(frame, "primary_domain", "") or "").strip().lower()
        observations = list(getattr(frame, "field_observations", []) or [])
        self_fields = {
            str(getattr(item, "field", "") or "").strip()
            for item in observations
            if str(getattr(item, "scope", "") or "").strip() == "self"
        }
        partner_fields = {
            str(getattr(item, "field", "") or "").strip()
            for item in observations
            if str(getattr(item, "scope", "") or "").strip() == "partner"
        }
        contact_fields = {
            str(getattr(item, "field", "") or "").strip()
            for item in observations
            if str(getattr(item, "scope", "") or "").strip() == "contact"
        }
        user_questions = list(getattr(frame, "user_questions", []) or [])

        if primary_domain == "faq" or user_questions:
            topic = str(getattr(user_questions[0], "topic", "") or "").strip() if user_questions else ""
            return "faq_concern", topic or "structured_question"
        if primary_domain == "risk":
            return "risk_guard", str(getattr(fallback_result, "subtype", "") or "").strip() or "risk"
        if primary_domain == "boundary":
            return "refusal_boundary_complaint", str(getattr(fallback_result, "subtype", "") or "").strip() or "boundary"
        if primary_domain == "closing":
            return "closing_exit", str(getattr(fallback_result, "subtype", "") or "").strip() or "closing"
        if primary_domain in {"profile", "mixed"} and (self_fields or partner_fields):
            observed_count = len(self_fields | partner_fields | contact_fields)
            subtype = "multi_slot_compound" if observed_count >= 2 else "single_slot_answer"
            return "profile_answer", subtype
        if primary_domain == "contact" and contact_fields:
            return "contact_answer", "contact_provided"
        return fallback_result.primary_turn_type, fallback_result.subtype
