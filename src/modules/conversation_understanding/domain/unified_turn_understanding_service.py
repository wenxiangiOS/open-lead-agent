from __future__ import annotations

import logging

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.ai_context_disambiguation_layer import AIContextDisambiguationLayer
from src.modules.conversation_understanding.domain.contextual_slot_governance_layer import (
    ContextualSlotGovernanceLayer,
)
from src.modules.conversation_understanding.domain.field_arbitration_layer import FieldArbitrationLayer
from src.modules.conversation_understanding.domain.field_derivation_layer import FieldDerivationLayer
from src.modules.conversation_understanding.domain.field_permission_layer import FieldPermissionLayer
from src.modules.conversation_understanding.domain.followup_planning_layer import FollowupPlanningLayer
from src.modules.conversation_understanding.domain.lexical_signal_layer import LexicalSignalLayer
from src.modules.conversation_understanding.domain.models import UnifiedTurnUnderstandingResult
from src.modules.conversation_understanding.domain.reply_act_classification_layer import ReplyActClassificationLayer
from src.modules.conversation_understanding.domain.semantic_understanding_layer import SemanticUnderstandingLayer

logger = logging.getLogger(__name__)


class UnifiedTurnUnderstandingService:
    """Single entrypoint for turn understanding.

    Stage 1 keeps current business behaviour stable by delegating semantic
    resolution to the existing TurnUnderstandingService and exposing a unified
    orchestration layer around it.
    """

    def __init__(self, semantic_service, ai_service) -> None:
        self.lexical_layer = LexicalSignalLayer(semantic_service)
        self.semantic_layer = SemanticUnderstandingLayer(semantic_service)
        self.ai_layer = AIContextDisambiguationLayer(ai_service)
        self.slot_governance_layer = ContextualSlotGovernanceLayer(semantic_service)
        self.reply_act_layer = ReplyActClassificationLayer()
        self.field_permission_layer = FieldPermissionLayer()
        self.field_arbitration_layer = FieldArbitrationLayer()
        self.field_derivation_layer = FieldDerivationLayer()
        self.followup_planning_layer = FollowupPlanningLayer()

    async def analyze(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:
        lexical_signals = self.lexical_layer.analyze(turn_input)
        semantic_result = self.semantic_layer.analyze(turn_input)
        ai_result = await self.ai_layer.analyze(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            turn_input=turn_input,
        )
        decision_source = "semantic"
        if ai_result.used:
            decision_source = "ai_disambiguation"
        elif lexical_signals.can_short_circuit:
            decision_source = "lexical+semantic"
        base_result = ai_result.overridden_result if ai_result.used and ai_result.overridden_result else semantic_result
        governed_result = self.slot_governance_layer.govern(
            turn_input=turn_input,
            result=base_result,
        )
        question_state = self._get_question_state(turn_input)
        reply_act_result = self.reply_act_layer.classify(
            turn_input=turn_input,
            semantic_result=governed_result,
            question_state=question_state,
        )
        field_permission_result = self.field_permission_layer.decide(
            turn_input=turn_input,
            semantic_result=governed_result,
            reply_act_result=reply_act_result,
            question_state=question_state,
        )
        governed_result = self.field_permission_layer.filter_result(
            result=governed_result,
            permission_result=field_permission_result,
        )
        governed_result = self.field_arbitration_layer.arbitrate(
            result=governed_result,
            permission_result=field_permission_result,
        )
        governed_result = self.field_derivation_layer.derive(result=governed_result)
        if ai_result.used and ai_result.overridden_result:
            ai_result.overridden_result = governed_result
        else:
            semantic_result = governed_result
        unified_result = UnifiedTurnUnderstandingResult(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            ai_result=ai_result,
            decision_source=decision_source,
            reply_act_result=reply_act_result,
            field_permission_result=field_permission_result,
            resolved_field_evidence=dict(governed_result.resolved_field_evidence or {}),
            field_derivations=dict(governed_result.field_derivations or {}),
        )
        lexical_true = sorted(name for name, value in (lexical_signals.signals or {}).items() if value)
        inferred_occupation_candidate = str(
            getattr(turn_input.user_profile, "occupation_inference_candidate", "") or ""
        ).strip()
        inferred_occupation_confidence = 0.0
        partner_requirement = str((semantic_result.resolved_slots or {}).get("partner_requirement") or "").strip()
        if (
            not inferred_occupation_candidate
            and partner_requirement
            and hasattr(self.semantic_layer.semantic_service, "_extract_occupation_inference_candidate_from_partner_requirement")
        ):
            extraction_service = getattr(self.semantic_layer.semantic_service.chat_service, "extraction_service", None)
            if extraction_service is not None and hasattr(extraction_service, "_infer_occupation_candidate_from_partner_requirement"):
                (
                    inferred_occupation_candidate,
                    inferred_occupation_confidence,
                    _,
                ) = extraction_service._infer_occupation_candidate_from_partner_requirement(  # noqa: SLF001
                    partner_requirement
                )
                inferred_occupation_candidate = str(inferred_occupation_candidate or "").strip()
            else:
                inferred_occupation_candidate = str(
                    self.semantic_layer.semantic_service._extract_occupation_inference_candidate_from_partner_requirement(  # noqa: SLF001
                        partner_requirement
                    )
                    or ""
                ).strip()
        logger.info(
            "[unified_turn_understanding] source=%s lexical=%s semantic=%s/%s conf=%.2f ai_applied=%s ai_used=%s ai_reason=%s reply_act=%s occupation_inference_candidate=%s occupation_inference_confidence=%s",
            decision_source,
            lexical_true,
            semantic_result.primary_turn_type,
            semantic_result.subtype,
            float(semantic_result.confidence or 0.0),
            ai_result.applied,
            ai_result.used,
            ai_result.reason or "-",
            reply_act_result.reply_act or "-",
            inferred_occupation_candidate or "-",
            f"{float(inferred_occupation_confidence or 0.66):.2f}" if inferred_occupation_candidate else "-",
        )
        return unified_result.to_turn_understanding_result()

    @staticmethod
    def _get_question_state(turn_input: TurnUnderstandingInput) -> dict:
        profile = getattr(turn_input, "user_profile", None)
        raw = getattr(profile, "last_question_state", None) if profile is not None else None
        if isinstance(raw, dict):
            return dict(raw)
        return {}
