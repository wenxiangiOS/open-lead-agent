from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import (
    PreGenerationResolutionMeta,
    TurnUnderstandingResult,
)


@dataclass
class OpeningIntentSignal:
    intent: str = ""
    confidence: float = 0.0
    secondary_intent: str | None = None
    parse_failed: bool = False


@dataclass
class TurnExecutionPreparation:
    understanding: TurnUnderstandingResult
    decision_profile: UserProfile
    turn_decision: TurnDecision
    response_channel: str
    pre_generation_resolution: PreGenerationResolutionMeta | None = None


@dataclass
class AlreadyEndedPreparation:
    route_name: str
    final_response: str
    payload: Optional[Dict[str, Any]]


@dataclass
class CollectionPhaseOutcome:
    user_profile: UserProfile
    collection_result: Dict[str, Any]
    ai_response: str
    turn_decision: TurnDecision
    response_channel: str
    extracted_fields_count: int
    contact_gate_before: bool


@dataclass
class GenerationCollectionPhaseOutcome:
    user_profile: UserProfile
    ai_response: str
    infra_fail: bool
    infra_fail_reason: str
    collection_result: Dict[str, Any]
    turn_decision: TurnDecision
    response_channel: str
    extracted_fields_count: int
    contact_gate_before: bool
    preset_payload: Optional[tuple[str, Dict[str, Any]]]
    ai_call_ms: int
    extract_fuse_ms: int
    collection_process_ms: int
