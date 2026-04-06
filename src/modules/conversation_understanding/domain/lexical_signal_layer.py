from __future__ import annotations

import re

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput
from src.modules.conversation_understanding.domain.models import LexicalSignalSet


class LexicalSignalLayer:
    """High-recall lexical signal layer.

    This layer only emits coarse signals and a very small set of safe short-circuit
    decisions for low-ambiguity cases. It does not replace semantic resolution.
    """

    def __init__(self, semantic_service) -> None:
        self.semantic_service = semantic_service

    def analyze(self, turn_input: TurnUnderstandingInput) -> LexicalSignalSet:
        message = str(turn_input.user_message or "").strip()
        message_count = int(turn_input.message_count or 0)
        relationship_seek = bool(
            message
            and re.search(
                r"((?:找|介绍|介绍下|牵线|安排|相亲|脱单).{0,6}(?:对象|另一半|男朋友|女朋友|男生|女生)|帮(?:我|忙)?.{0,4}(?:找|介绍|牵线|安排).{0,6}(?:对象|另一半|男朋友|女朋友|男生|女生))",
                message,
            )
        )
        signals = {
            "greeting": bool(message and self.semantic_service._is_stable_opening_greeting(message)),  # noqa: SLF001
            "relationship_seek": relationship_seek,
            "faq": bool(message and self.semantic_service._detect_faq_intent(message)),  # noqa: SLF001
            "refusal": bool(message and self.semantic_service._looks_like_refusal(message)),  # noqa: SLF001
            "boundary": bool(message and self.semantic_service._is_boundary_pause(message, turn_input.user_profile)),  # noqa: SLF001
            "contact": bool(message and any(token in message for token in ("电话", "手机号", "号码", "微信", "联系方式"))),
            "closing": bool(message and self.semantic_service._classify_withdraw_intent(message)),  # noqa: SLF001
            "risk": bool(message and self.semantic_service._is_risk_guard(message)),  # noqa: SLF001
            "complaint": bool(message and self.semantic_service._is_complaint_message(message)),  # noqa: SLF001
        }

        short_circuit_type = None
        confidence = 0.0
        if signals["risk"]:
            short_circuit_type = "risk_guard"
            confidence = 0.99
        elif signals["closing"]:
            short_circuit_type = "closing_exit"
            confidence = 0.97
        elif message_count <= 1 and signals["greeting"] and not any(
            signals[key] for key in ("faq", "refusal", "boundary", "contact", "closing", "risk", "complaint")
        ):
            short_circuit_type = "opening_greeting"
            confidence = 0.93

        return LexicalSignalSet(
            signals=signals,
            can_short_circuit=bool(short_circuit_type),
            short_circuit_type=short_circuit_type,
            confidence=confidence,
        )
