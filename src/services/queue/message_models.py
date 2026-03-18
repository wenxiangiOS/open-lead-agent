from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


SESSION_IDLE = "IDLE"
SESSION_DEBOUNCING = "DEBOUNCING"
SESSION_RUNNING = "RUNNING"


@dataclass
class IncomingMessage:
    account_id: str
    dialog_id: Optional[str]
    content: str
    platform_msg_id: str
    timestamp: Optional[str]
    sex: Optional[str] = None
    cancel_like: bool = False
    force_flush: bool = False


@dataclass
class QueueSession:
    account_id: str
    version: int = 1
    state: str = SESSION_IDLE
    generation: int = 0
    debounce_until_ms: int = 0
    first_enqueue_at_ms: int = 0
    last_consumed_seq: int = 0
    max_enqueued_seq: int = 0
    active_turn_id: str = ""
    dirty: bool = False
    fail_streak: int = 0
    updated_at_ms: int = 0


@dataclass
class TurnContext:
    turn_id: str
    account_id: str
    generation: int
    start_seq: int
    end_seq: int
    dialog_id: Optional[str] = None
    sex: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class OutboxJob:
    job_id: str
    account_id: str
    turn_id: str
    generation: int
    reply_text: str
    dialog_id: Optional[str]
    retry_count: int
    next_retry_at_ms: int


@dataclass
class EnqueueResult:
    accepted: bool
    duplicate: bool
    session_state: str
    seq: int
    status: str = "queued"
    pending: int = 0
