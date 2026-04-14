from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.modules.conversation.domain.turn_understanding_models import (
    ResolvedFieldEvidence,
    TurnPriorityDecision,
    TurnUnderstandingResult,
)


@dataclass
class LexicalSignalSet:
    signals: Dict[str, bool] = field(default_factory=dict)
    can_short_circuit: bool = False
    short_circuit_type: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ReplyActClassificationResult:
    reply_act: str = "unknown"
    confidence: float = 0.0
    reason: str = ""


@dataclass
class FieldPermissionResult:
    allowed_fields: set[str] = field(default_factory=set)
    blocked_fields: set[str] = field(default_factory=set)
    priority_fields: list[str] = field(default_factory=list)
    allowed_scope: str = "mixed"
    allow_mixed_answer: bool = False


@dataclass
class UnifiedTurnUnderstandingResult:
    lexical_signals: LexicalSignalSet
    semantic_result: TurnUnderstandingResult
    decision_source: str = "semantic"
    reply_act_result: ReplyActClassificationResult = field(default_factory=ReplyActClassificationResult)
    field_permission_result: FieldPermissionResult = field(default_factory=FieldPermissionResult)
    priority_decision: TurnPriorityDecision | None = None
    resolved_field_evidence: Dict[str, ResolvedFieldEvidence] = field(default_factory=dict)
    field_derivations: Dict[str, str] = field(default_factory=dict)
    semantic_frame: Optional["TurnSemanticFrame"] = None
    persistence_plan: Optional["TurnPersistencePlan"] = None
    notes: list[str] = field(default_factory=list)

    def to_turn_understanding_result(self) -> TurnUnderstandingResult:
        result = self.semantic_result
        merged_notes = list(result.notes or [])
        lexical_true = sorted(name for name, value in (self.lexical_signals.signals or {}).items() if value)
        if lexical_true:
            merged_notes.append(f"lexical_signals={','.join(lexical_true)}")
        merged_notes.append(f"understanding_source={self.decision_source}")
        if self.reply_act_result.reply_act and self.reply_act_result.reply_act != "unknown":
            merged_notes.append(f"reply_act={self.reply_act_result.reply_act}")
        if self.field_permission_result.allowed_fields:
            merged_notes.append(
                f"allowed_fields={','.join(sorted(self.field_permission_result.allowed_fields))}"
            )
        if self.priority_decision is not None:
            merged_notes.append(f"priority_task={self.priority_decision.primary_task}")
            merged_notes.append(f"priority_reason={self.priority_decision.decision_reason}")
        if self.notes:
            merged_notes.extend(str(item).strip() for item in self.notes if str(item).strip())
        result.resolved_field_evidence = dict(self.resolved_field_evidence or getattr(result, "resolved_field_evidence", {}) or {})
        result.field_derivations = dict(self.field_derivations or getattr(result, "field_derivations", {}) or {})
        result.priority_decision = self.priority_decision
        result.notes = merged_notes
        if self.semantic_frame is not None:
            setattr(result, "semantic_frame", self.semantic_frame)
        if self.persistence_plan is not None:
            setattr(result, "persistence_plan", self.persistence_plan)
        return result


@dataclass
class TurnInputSnapshot:
    user_message: str
    last_response: str
    message_count: int
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    in_contact_flow: bool = False
    pending_confirmation_field: Optional[str] = None
    prompt_state: Dict[str, Any] = field(default_factory=dict)
    prior_semantic_summary: Dict[str, Any] = field(default_factory=dict)
    user_profile: Any = None


@dataclass
class UserQuestion:
    topic: str
    question_text: str
    confidence: float


@dataclass
class FieldObservation:
    field: str
    value: Any
    normalized_value: Any
    scope: str
    owner: str
    evidence_text: str
    evidence_span: str | None
    confidence: float
    write_mode: str
    source: str
    raw_value: Any = None
    unit: str | None = None
    relation: str | None = None
    conflict_hint: str | None = None


@dataclass
class TurnSemanticFrame:
    version: str
    source: str
    primary_domain: str
    acts: list[str] = field(default_factory=list)
    user_questions: list[UserQuestion] = field(default_factory=list)
    field_observations: list[FieldObservation] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    boundaries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class AcceptedField:
    field: str
    value: Any
    normalized_value: Any
    scope: str
    evidence_text: str
    confidence: float
    acceptance_reason: str
    update_action: str
    persistence_state: str = "committed"
    risk_level: str = "normal"
    source_channel: str = "unknown"
    field_version: int = 1
    expected_profile_version: int | None = None
    expected_profile_updated_at: str | None = None


@dataclass
class PendingField:
    field: str
    candidate_value: Any
    reason: str
    scope: str = "self"
    confirmation_question_type: str | None = None
    persistence_state: str = "pending_confirm"
    risk_level: str = "normal"
    source_channel: str = "unknown"


@dataclass
class RejectedField:
    field: str
    candidate_value: Any
    reason: str
    scope: str = "self"


@dataclass
class PromptState:
    prompt_type: str
    main_target: str | None
    side_targets: list[str] = field(default_factory=list)
    expected_scopes: list[str] = field(default_factory=list)
    allows_mixed_answer: bool = True
    pending_confirmations: list[str] = field(default_factory=list)


@dataclass
class TurnPersistencePlan:
    accepted_fields: list[AcceptedField] = field(default_factory=list)
    provisional_fields: list[AcceptedField] = field(default_factory=list)
    pending_fields: list[PendingField] = field(default_factory=list)
    rejected_fields: list[RejectedField] = field(default_factory=list)
    observation_log: list[FieldObservation] = field(default_factory=list)
    update_prompt_state: Optional[PromptState] = None
    next_resume_target: str | None = None
    expected_profile_version: int | None = None
    expected_profile_updated_at: str | None = None
    strategy_version: str = "quality_first_v2"
