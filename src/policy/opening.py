"""开场缓冲策略。

用户刚看到系统开场白后，如果只回一句简单问候，先低压接住，
不要马上切入字段采集。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.templates.config import TemplateConfig
from src.understanding import TurnSemanticFrame


@dataclass(frozen=True)
class OpeningDecision:
    reason: str
    message: str


class OpeningPolicy:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def evaluate(
        self,
        *,
        user_message: str,
        profile: dict[str, Any],
        collected_this_turn: dict[str, Any],
        recent_history: list[dict[str, str]],
        semantic_frame: TurnSemanticFrame | None,
    ) -> OpeningDecision | None:
        if not self.template.opening.enabled:
            return None
        if collected_this_turn or self._has_profile_values(profile):
            return None
        if recent_history:
            return None
        if not self._is_simple_greeting(user_message, semantic_frame):
            return None

        message = (
            self.template.opening.greeting_response
            or "你好呀，我在呢。你可以先简单说下自己的情况，我先了解一下。"
        )
        return OpeningDecision(reason="opening:greeting_pause", message=message)

    def _has_profile_values(self, profile: dict[str, Any]) -> bool:
        return any(value not in (None, "", [], {}) for value in profile.values())

    def _is_simple_greeting(
        self,
        user_message: str,
        semantic_frame: TurnSemanticFrame | None,
    ) -> bool:
        text = user_message.strip().lower()
        compact = "".join(char for char in text if char.isalnum() or "\u4e00" <= char <= "\u9fff")
        greetings = {
            "你好",
            "您好",
            "你好呀",
            "你好啊",
            "哈喽",
            "嗨",
            "hi",
            "hello",
            "hey",
        }
        if compact in {item.lower() for item in greetings}:
            return True
        if len(compact) <= 8 and semantic_frame is not None:
            return semantic_frame.has_intent("greeting", "opening")
        return False
