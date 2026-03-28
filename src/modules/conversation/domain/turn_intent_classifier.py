from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class TurnIntentResult:
    intent: str = "general"
    confidence: float = 0.0
    reason_code: str = ""
    suppress_direct_profile_ask: bool = False
    suppress_contact_push: bool = False
    prefer_self_intro_invite: bool = False


class TurnIntentClassifier:
    """轻量回合意图识别器。

    当前仅启用开场低压了解保护，不接管其他主流程。
    """

    _OPENING_PROBE_MARKERS = (
        "想找对象",
        "先了解下",
        "先看看情况",
        "先问问情况",
        "认真聊聊",
    )

    _LEGACY_SOFT_OPENING_EXAMPLES = {
        "先了解下",
        "先了解一下",
        "了解下",
        "了解一下",
        "先看看",
        "看看情况",
        "问问情况",
        "先问问情况",
        "想了解下",
        "想了解一下",
        "先聊聊",
    }

    _LOW_PRESSURE_OPENING_PATTERNS = (
        re.compile(r"^(我)?(先)?了解(一下|下|了解)?$"),
        re.compile(r"^(我)?(先)?看看(情况)?(再说)?$"),
        re.compile(r"^(我)?(先)?聊聊(吧)?$"),
        re.compile(r"^(我)?想(先)?了解(一下|下|了解)?$"),
        re.compile(r"^(就是|就|只是)?想先问问情况$"),
        re.compile(r"^(我)?问问你?情况$"),
        re.compile(r"^(我)?想问问你?情况$"),
        re.compile(r"^(我)?先问问你?情况$"),
        re.compile(r"^(就是|就|只是)?想先看看(情况)?$"),
        re.compile(r"^(就是|就|只是)?想先了解(一下|下|了解)?$"),
        re.compile(r"^(我)?(先)?认识(一下|认识)(再说)?$"),
        re.compile(r"^(我)?(先)?问问情况$"),
        re.compile(r"^(我)?(先)?看看(吧)?$"),
    )

    def classify_opening_low_pressure(
        self,
        *,
        user_message: str,
        last_response: str,
        message_count: int,
        has_opening_fields: bool,
        has_faq_intent: bool,
        has_boundary_pause: bool,
        has_risk_guard: bool,
    ) -> TurnIntentResult:
        if message_count > 2:
            return TurnIntentResult()
        if not last_response or not any(marker in last_response for marker in self._OPENING_PROBE_MARKERS):
            return TurnIntentResult()
        if has_opening_fields or has_faq_intent or has_boundary_pause or has_risk_guard:
            return TurnIntentResult()

        normalized = self._normalize_message(user_message)
        if not normalized:
            return TurnIntentResult()

        if normalized in self._LEGACY_SOFT_OPENING_EXAMPLES:
            return self._build_low_pressure_result("legacy_soft_opening_example", 0.9)

        if any(pattern.fullmatch(normalized) for pattern in self._LOW_PRESSURE_OPENING_PATTERNS):
            return self._build_low_pressure_result("normalized_low_pressure_opening", 0.86)

        return TurnIntentResult()

    @staticmethod
    def _build_low_pressure_result(reason_code: str, confidence: float) -> TurnIntentResult:
        return TurnIntentResult(
            intent="low_pressure_opening",
            confidence=confidence,
            reason_code=reason_code,
            suppress_direct_profile_ask=True,
            suppress_contact_push=True,
            prefer_self_intro_invite=True,
        )

    @staticmethod
    def _normalize_message(text: str) -> str:
        message = str(text or "").strip().lower()
        if not message:
            return ""

        normalized = re.sub(r"[\s,，。！？!?~～、:：;；\"'`()（）]+", "", message)
        normalized = re.sub(r"(呢|呀|哈|啊|哦|噢|嘛|啦|呗|吧)+$", "", normalized)
        normalized = re.sub(r"^(那|那就|那我|我就|我想|我先|那先|就是想|就想|只是想)", "", normalized)
        normalized = re.sub(r"(呀|呢|哈|啊|哦|噢|嘛|啦|呗|吧)+$", "", normalized)
        return normalized
