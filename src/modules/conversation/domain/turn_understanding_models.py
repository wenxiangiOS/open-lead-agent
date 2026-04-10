from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Literal, Optional


TurnType = Literal[
    "opening",
    "faq_concern",
    "profile_answer",
    "contact_answer",
    "confirmation",
    "refusal_boundary_complaint",
    "correction",
    "invalid_input",
    "closing_exit",
    "risk_guard",
]


@dataclass
class SlotCandidate:
    value: str
    confidence: float
    source: str
    source_text: str
    scope: str = "mixed"
    source_span: str = ""


@dataclass
class BlockedSlot:
    value: str
    reason: str
    source: str
    source_text: str


@dataclass
class ResolvedFieldEvidence:
    field: str
    value: str
    scope: str
    source_span: str
    source_text: str
    confidence: float
    source_type: str
    derived_from: Optional[str] = None


@dataclass
class PreGenerationResolutionMeta:
    source: str = ""
    resolved_fields: List[str] = field(default_factory=list)
    transition_reason: str = ""


@dataclass
class TurnUnderstandingInput:
    user_message: str
    last_response: str
    message_count: int
    user_profile: object
    conversation_context: dict
    in_contact_flow: bool
    pending_confirmation_field: Optional[str] = None


@dataclass
class TurnUnderstandingResult:
    primary_turn_type: TurnType
    subtype: Optional[str] = None
    complaint_reason: Optional[str] = None
    resume_profile_collection: bool = False
    post_answer_reentry: bool = False
    secondary_signals: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    slot_candidates: Dict[str, SlotCandidate] = field(default_factory=dict)
    resolved_slots: Dict[str, str] = field(default_factory=dict)
    resolved_field_evidence: Dict[str, ResolvedFieldEvidence] = field(default_factory=dict)
    field_derivations: Dict[str, str] = field(default_factory=dict)
    blocked_slots: Dict[str, BlockedSlot] = field(default_factory=dict)
    answer_first: bool = False
    resume_hint: Optional[str] = None
    context_ack_type: Optional[str] = None
    context_ack_payload: Dict[str, str] = field(default_factory=dict)
    context_ack_occupation: Optional[str] = None
    context_ack_location: Optional[str] = None
    context_ack_preference: Optional[str] = None
    context_ack_field_ack: Optional[str] = None
    soft_retry_field: Optional[str] = None
    pre_generation_resolution: Optional[PreGenerationResolutionMeta] = None
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)

    @staticmethod
    def build_pre_generation_compat_payload(
        *,
        source: str = "",
        resolved_fields: Optional[List[str]] = None,
        transition_reason: str = "",
    ) -> Dict[str, str]:
        payload: Dict[str, str] = {}
        if source:
            payload["pre_generation_resolution_source"] = source
        if resolved_fields:
            payload["pre_generation_resolved_fields"] = ",".join(resolved_fields)
        if transition_reason:
            payload["pre_generation_transition_reason"] = transition_reason
        return payload

    def get_pre_generation_compat_payload(self) -> Dict[str, str]:
        meta = self.pre_generation_resolution
        if meta is None:
            return {}
        transition_reason = meta.transition_reason or str(
            self.context_ack_payload.get("pre_generation_transition_reason") or ""
        )
        return self.build_pre_generation_compat_payload(
            source=meta.source,
            resolved_fields=list(meta.resolved_fields or []),
            transition_reason=transition_reason,
        )

    def set_pre_generation_transition_reason(self, reason: str) -> None:
        meta = self.pre_generation_resolution or PreGenerationResolutionMeta()
        meta.transition_reason = reason
        self.pre_generation_resolution = meta
        self.context_ack_payload.update(
            self.build_pre_generation_compat_payload(
                source=meta.source,
                resolved_fields=list(meta.resolved_fields or []),
                transition_reason=meta.transition_reason,
            )
        )

    def set_pre_generation_resolution(
        self,
        *,
        source: str,
        resolved_fields: List[str],
        default_transition_reason: str,
    ) -> None:
        meta = self.pre_generation_resolution or PreGenerationResolutionMeta()
        meta.source = source
        meta.resolved_fields = list(resolved_fields)
        if not meta.transition_reason:
            meta.transition_reason = default_transition_reason
        self.pre_generation_resolution = meta
        self.context_ack_payload.update(
            self.build_pre_generation_compat_payload(
                source=meta.source,
                resolved_fields=list(meta.resolved_fields or []),
                transition_reason=meta.transition_reason,
            )
        )

    def to_dict(self) -> dict:
        def _serialize_slot_map(slot_map: Dict[str, object]) -> dict:
            return {
                field_name: value.__dict__ if hasattr(value, "__dict__") else value
                for field_name, value in slot_map.items()
            }

        return {
            "primary_turn_type": self.primary_turn_type,
            "subtype": self.subtype,
            "complaint_reason": self.complaint_reason,
            "resume_profile_collection": self.resume_profile_collection,
            "post_answer_reentry": self.post_answer_reentry,
            "secondary_signals": list(self.secondary_signals),
            "risk_flags": list(self.risk_flags),
            "slot_candidates": _serialize_slot_map(self.slot_candidates),
            "resolved_slots": dict(self.resolved_slots),
            "resolved_field_evidence": _serialize_slot_map(self.resolved_field_evidence),
            "field_derivations": dict(self.field_derivations),
            "blocked_slots": _serialize_slot_map(self.blocked_slots),
            "answer_first": self.answer_first,
            "resume_hint": self.resume_hint,
            "context_ack_type": self.context_ack_type,
            "context_ack_payload": dict(self.context_ack_payload),
            "context_ack_occupation": self.context_ack_occupation,
            "context_ack_location": self.context_ack_location,
            "context_ack_preference": self.context_ack_preference,
            "context_ack_field_ack": self.context_ack_field_ack,
            "soft_retry_field": self.soft_retry_field,
            "pre_generation_resolution": asdict(self.pre_generation_resolution) if self.pre_generation_resolution else None,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }
