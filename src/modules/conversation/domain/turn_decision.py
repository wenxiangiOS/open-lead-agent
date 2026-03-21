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
    ask_field: str | None = None
    response_channel: str = "model"  # model | fixed_template | quick_faq
    tone_policy: dict[str, Any] = field(default_factory=dict)

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "risk": self.risk,
            "stage": self.stage,
            "next_action": self.next_action,
            "ask_field": self.ask_field,
            "response_channel": self.response_channel,
            "tone_policy": self.tone_policy,
        }
