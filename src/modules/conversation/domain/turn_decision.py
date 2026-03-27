from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnDecision:
    """单轮对话结构化决策（唯一真相）。"""

    intent: str = "general"
    risk: str = "none"
    stage: str = "collect"
    next_action: str = "continue"
    primary_move: str = "ack_and_ask"
    ask_field: str | None = None
    prioritize_user_question: bool = False
    allow_contact_target: bool = True
    allow_medium_target: bool = True
    response_channel: str = "model"  # model | quick_faq
    tone_policy: dict[str, Any] = field(default_factory=dict)
    # Phase 2: 投诉修复状态
    in_repair_mode: bool = False
    repair_cooldown_remaining: int = 0
    user_concern_type: str | None = None
    resume_mode: str | None = None
    resume_target: str | None = None
    resume_applied: bool = False
    followup_topic: str | None = None
    context_ack_required: bool = False
    context_ack_type: str | None = None
    context_ack_payload: dict[str, Any] = field(default_factory=dict)

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "risk": self.risk,
            "stage": self.stage,
            "next_action": self.next_action,
            "primary_move": self.primary_move,
            "ask_field": self.ask_field,
            "prioritize_user_question": self.prioritize_user_question,
            "allow_contact_target": self.allow_contact_target,
            "allow_medium_target": self.allow_medium_target,
            "response_channel": self.response_channel,
            "tone_policy": self.tone_policy,
            "in_repair_mode": self.in_repair_mode,
            "repair_cooldown_remaining": self.repair_cooldown_remaining,
            "user_concern_type": self.user_concern_type,
            "resume_mode": self.resume_mode,
            "resume_target": self.resume_target,
            "resume_applied": self.resume_applied,
            "followup_topic": self.followup_topic,
            "context_ack_required": self.context_ack_required,
            "context_ack_type": self.context_ack_type,
            "context_ack_payload": self.context_ack_payload,
        }
