from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult


@dataclass
class LexicalSignalSet:
    signals: Dict[str, bool] = field(default_factory=dict)
    can_short_circuit: bool = False
    short_circuit_type: Optional[str] = None
    confidence: float = 0.0


@dataclass
class AIContextDisambiguationResult:
    applied: bool = False
    used: bool = False
    overridden_result: Optional[TurnUnderstandingResult] = None
    raw_response: str = ""
    reason: str = ""


@dataclass
class UnifiedTurnUnderstandingResult:
    lexical_signals: LexicalSignalSet
    semantic_result: TurnUnderstandingResult
    ai_result: AIContextDisambiguationResult = field(default_factory=AIContextDisambiguationResult)
    decision_source: str = "semantic"
    notes: list[str] = field(default_factory=list)

    def to_turn_understanding_result(self) -> TurnUnderstandingResult:
        result = self.ai_result.overridden_result if self.ai_result.used and self.ai_result.overridden_result else self.semantic_result
        merged_notes = list(result.notes or [])
        lexical_true = sorted(name for name, value in (self.lexical_signals.signals or {}).items() if value)
        if lexical_true:
            merged_notes.append(f"lexical_signals={','.join(lexical_true)}")
        merged_notes.append(f"understanding_source={self.decision_source}")
        if self.ai_result.applied and self.ai_result.reason:
            merged_notes.append(f"ai_disambiguation={self.ai_result.reason}")
        result.notes = merged_notes
        return result
