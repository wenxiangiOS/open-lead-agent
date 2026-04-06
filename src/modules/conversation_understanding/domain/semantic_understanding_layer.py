from __future__ import annotations

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult


class SemanticUnderstandingLayer:
    """Semantic layer that preserves current project behaviour.

    Stage 1 intentionally reuses the existing TurnUnderstandingService so the
    project can unify the entrypoint without rewriting current business logic.
    """

    def __init__(self, semantic_service) -> None:
        self.semantic_service = semantic_service

    def analyze(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:
        analyze_without_governance = getattr(self.semantic_service, "analyze_without_slot_governance", None)
        if callable(analyze_without_governance):
            return analyze_without_governance(turn_input)
        return self.semantic_service.analyze(turn_input)
