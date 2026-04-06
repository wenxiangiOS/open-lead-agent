from __future__ import annotations

import logging

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.ai_context_disambiguation_layer import AIContextDisambiguationLayer
from src.modules.conversation_understanding.domain.contextual_slot_governance_layer import (
    ContextualSlotGovernanceLayer,
)
from src.modules.conversation_understanding.domain.followup_planning_layer import FollowupPlanningLayer
from src.modules.conversation_understanding.domain.lexical_signal_layer import LexicalSignalLayer
from src.modules.conversation_understanding.domain.models import UnifiedTurnUnderstandingResult
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
        if ai_result.used and ai_result.overridden_result:
            ai_result.overridden_result = governed_result
        else:
            semantic_result = governed_result
        unified_result = UnifiedTurnUnderstandingResult(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            ai_result=ai_result,
            decision_source=decision_source,
        )
        lexical_true = sorted(name for name, value in (lexical_signals.signals or {}).items() if value)
        logger.info(
            "[unified_turn_understanding] source=%s lexical=%s semantic=%s/%s conf=%.2f ai_applied=%s ai_used=%s ai_reason=%s",
            decision_source,
            lexical_true,
            semantic_result.primary_turn_type,
            semantic_result.subtype,
            float(semantic_result.confidence or 0.0),
            ai_result.applied,
            ai_result.used,
            ai_result.reason or "-",
        )
        return unified_result.to_turn_understanding_result()
