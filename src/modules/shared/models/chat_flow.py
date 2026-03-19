from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuleCheckResult:
    handled: bool
    response_text: Optional[str] = None
    response_payload: Optional[Dict[str, Any]] = None
    track_asked_fields: bool = False


@dataclass
class ProfileCollectionResult:
    collection_result: Dict[str, Any]
    policy_decision: Any = None
    user_profile: Any = None


@dataclass
class ContactDecision:
    next_action: str
    prompt_instruction: str = ""
    should_end_conversation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
