from __future__ import annotations

import json
import logging
import os
import re

from src.core.exceptions import AIServiceException
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.models import AIContextDisambiguationResult, LexicalSignalSet

logger = logging.getLogger(__name__)


class AIContextDisambiguationLayer:
    """Conservative AI disambiguation layer.

    It is intentionally narrow in stage 1 so the new understanding pipeline can
    land without changing current dialogue policy behaviour.
    """

    def __init__(self, ai_service) -> None:
        self.ai_service = ai_service

    FALLBACK_SUBTYPES = {
        "opening_clarify",
        "connective_opening",
        "ambiguous_short_answer",
        "garbled_or_typo",
    }

    HIGH_VALUE_TURN_TYPES = {
        "opening",
        "contact_answer",
        "closing_exit",
    }

    async def analyze(
        self,
        *,
        lexical_signals: LexicalSignalSet,
        semantic_result: TurnUnderstandingResult,
        turn_input: TurnUnderstandingInput,
    ) -> AIContextDisambiguationResult:
        ai_reason = self._should_use_ai(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            turn_input=turn_input,
        )
        if not ai_reason:
            return AIContextDisambiguationResult(applied=False, reason="skipped")

        if self.ai_service is None:
            return AIContextDisambiguationResult(applied=False, reason=f"{ai_reason}:ai_service_unavailable")

        system_prompt = (
            "你是一个单轮对话理解消歧器。"
            "你只能在给定候选中选择最合适的一项。"
            "请只输出一行 JSON，不要输出解释。"
            '格式：{"primary_turn_type":"...","subtype":"...","confidence":0.00}'
        )
        message = str(turn_input.user_message or "").strip()
        last_response = str(turn_input.last_response or "").strip()
        lexical_true = [name for name, value in (lexical_signals.signals or {}).items() if value]
        prompt = (
            f"用户消息：{message or '-'}\n"
            f"上一轮回复：{last_response or '-'}\n"
            f"词库信号：{','.join(lexical_true) or '-'}\n"
            f"当前语义层判断：{semantic_result.primary_turn_type}/{semantic_result.subtype or '-'}\n"
            "可选 primary_turn_type：opening, faq_concern, profile_answer, contact_answer, confirmation, "
            "refusal_boundary_complaint, correction, invalid_input, closing_exit, risk_guard\n"
            "opening 常见 subtype：greeting, matchmaking_intent, opening_clarify, low_pressure_opening, service_confirmation_opening\n"
            "如果用户是在开场表达想找对象、想被介绍对象、想脱单、想找男朋友/女朋友，即使前面带了“你好/在吗”，优先判断为 opening/matchmaking_intent。\n"
            "如果当前判断已经合理，也输出相同结果。"
        )

        try:
            raw = await self.ai_service.generate_response(
                prompt,
                system_prompt,
                temperature=0.0,
                max_tokens=60,
                timeout=8.0,
            )
        except AIServiceException as exc:
            logger.warning("[unified_understanding.ai_disambiguation] failed: %s", exc)
            return AIContextDisambiguationResult(applied=True, used=False, reason=f"{ai_reason}:ai_call_failed")

        parsed = self._parse(raw)
        if not parsed:
            return AIContextDisambiguationResult(
                applied=True,
                used=False,
                raw_response=str(raw or ""),
                reason=f"{ai_reason}:unparseable",
            )

        primary_turn_type = parsed.get("primary_turn_type") or semantic_result.primary_turn_type
        subtype = parsed.get("subtype")
        confidence = float(parsed.get("confidence") or 0.0)

        if primary_turn_type == semantic_result.primary_turn_type and (subtype or "") == (semantic_result.subtype or ""):
            return AIContextDisambiguationResult(
                applied=True,
                used=False,
                raw_response=str(raw or ""),
                reason=f"{ai_reason}:same_as_semantic",
            )

        overridden = TurnUnderstandingResult(
            primary_turn_type=primary_turn_type,
            subtype=subtype,
            complaint_reason=semantic_result.complaint_reason,
            resume_profile_collection=semantic_result.resume_profile_collection,
            post_answer_reentry=semantic_result.post_answer_reentry,
            secondary_signals=list(semantic_result.secondary_signals or []),
            risk_flags=list(semantic_result.risk_flags or []),
            slot_candidates=dict(semantic_result.slot_candidates or {}),
            resolved_slots=dict(semantic_result.resolved_slots or {}),
            blocked_slots=dict(semantic_result.blocked_slots or {}),
            answer_first=semantic_result.answer_first,
            resume_hint=semantic_result.resume_hint,
            context_ack_type=semantic_result.context_ack_type,
            context_ack_payload=dict(semantic_result.context_ack_payload or {}),
            confidence=confidence or semantic_result.confidence,
            notes=list(semantic_result.notes or []),
        )
        return AIContextDisambiguationResult(
            applied=True,
            used=True,
            overridden_result=overridden,
            raw_response=str(raw or ""),
            reason=f"{ai_reason}:ai_override",
        )

    @staticmethod
    def _should_use_ai(
        *,
        lexical_signals: LexicalSignalSet,
        semantic_result: TurnUnderstandingResult,
        turn_input: TurnUnderstandingInput,
    ) -> str | None:
        forced_reason = AIContextDisambiguationLayer._should_force_ai_disambiguation(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            turn_input=turn_input,
        )
        if forced_reason:
            return forced_reason
        if os.getenv("UNIFIED_TURN_AI_DISAMBIGUATION_ENABLED", "0") not in {"1", "true", "TRUE"}:
            return None
        threshold = float(os.getenv("UNIFIED_TURN_AI_CONFIDENCE_THRESHOLD", "0.65"))
        if float(semantic_result.confidence or 0.0) < threshold:
            return "low_confidence"
        signals = lexical_signals.signals or {}
        conflict = (
            signals.get("faq") and signals.get("refusal")
            or signals.get("boundary") and bool(semantic_result.resolved_slots)
            or semantic_result.subtype in {"ambiguous_short_answer", "garbled_or_typo"}
        )
        if conflict:
            return "signal_conflict"
        return None

    @staticmethod
    def _should_force_ai_disambiguation(
        *,
        lexical_signals: LexicalSignalSet,
        semantic_result: TurnUnderstandingResult,
        turn_input: TurnUnderstandingInput,
    ) -> str | None:
        message = str(turn_input.user_message or "").strip()
        if not message:
            return None
        signals = lexical_signals.signals or {}
        if any(signals.get(name) for name in ("faq", "boundary", "refusal", "risk", "closing", "complaint")):
            return None

        if AIContextDisambiguationLayer._has_dirty_slots(semantic_result):
            return "dirty_slot"

        if semantic_result.subtype in AIContextDisambiguationLayer.FALLBACK_SUBTYPES:
            if signals.get("relationship_seek"):
                return "fallback_with_relationship_seek"
            if semantic_result.primary_turn_type in AIContextDisambiguationLayer.HIGH_VALUE_TURN_TYPES:
                return "high_value_fallback"
            return "global_fallback_subtype"

        if (
            semantic_result.primary_turn_type == "opening"
            and int(turn_input.message_count or 0) <= 1
            and semantic_result.subtype in {"opening_clarify", "greeting", "connective_opening"}
            and signals.get("relationship_seek")
        ):
            return "opening_relationship_seek"

        if (
            semantic_result.primary_turn_type == "opening"
            and int(turn_input.message_count or 0) <= 1
            and signals.get("greeting")
        ):
            normalized = re.sub(r"[\s,，。！？!?~～、]+", "", message)
            normalized = re.sub(r"(你好|您好|hi|hello|哈喽|嗨|在吗|在不|早上好|下午好|晚上好)+", "", normalized, flags=re.IGNORECASE)
            if len(normalized) >= 3:
                return "opening_composite_signal"

        if signals.get("relationship_seek") and semantic_result.subtype != "matchmaking_intent":
            return "strong_signal_not_consumed"

        return None

    @staticmethod
    def _has_dirty_slots(semantic_result: TurnUnderstandingResult) -> bool:
        resolved_slots = semantic_result.resolved_slots or {}
        partner_requirement = str(resolved_slots.get("partner_requirement") or "").strip()
        if partner_requirement and re.search(r"(找个男|找个女|个男这类|个女这类)", partner_requirement):
            return True
        return False

    @staticmethod
    def _parse(raw: str) -> dict | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
