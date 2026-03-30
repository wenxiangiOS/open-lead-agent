from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class BlockedSlot:
    value: str
    reason: str
    source: str
    source_text: str


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
    blocked_slots: Dict[str, BlockedSlot] = field(default_factory=dict)
    answer_first: bool = False
    resume_hint: Optional[str] = None
    context_ack_type: Optional[str] = None
    context_ack_payload: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)

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
            "blocked_slots": _serialize_slot_map(self.blocked_slots),
            "answer_first": self.answer_first,
            "resume_hint": self.resume_hint,
            "context_ack_type": self.context_ack_type,
            "context_ack_payload": dict(self.context_ack_payload),
            "confidence": self.confidence,
            "notes": list(self.notes),
        }
