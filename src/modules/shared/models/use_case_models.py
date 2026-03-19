from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProcessChatTurnCommand:
    question: str
    account_id: str
    dialog_id: Optional[str] = None
    sex: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class ProcessChatTurnResult:
    success: bool
    response: str
    dialog_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestMessageCommand:
    account_id: str
    message: str
    platform_msg_id: str
    dialog_id: Optional[str] = None
    timestamp: Optional[str] = None
    sex: Optional[str] = None


@dataclass
class IngestMessageResult:
    success: bool
    accepted: bool
    status: str
    session_state: Optional[str] = None
    seq: int = 0
    pending: int = 0
    max_pending: int = 0
    cancel_like: bool = False
    force_flush: bool = False
    payload: Dict[str, Any] = field(default_factory=dict)
