from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TurnMutationSet:
    profile_dirty: bool = False
    profile: Optional[Dict[str, Any]] = None
    state_dirty: bool = False
    state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnDraft:
    turn_id: str
    conversation_key: str
    profile_key: str
    generation: int
    covered_start_seq: int
    covered_end_seq: int
    dialog_id: Optional[str]
    reply_text: str
    mutation_set: TurnMutationSet
    created_at_ms: int
