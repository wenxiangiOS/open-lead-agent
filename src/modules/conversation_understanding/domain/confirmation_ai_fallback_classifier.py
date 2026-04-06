from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


@dataclass
class ConfirmationFallbackDecision:
    result: str
    field: str = ""


class ConfirmationAIFallbackClassifier:
    """用于短确认回复的语义消歧，不属于普通表达主链。"""

    def __init__(self, *, ai_service: Any) -> None:
        self.ai_service = ai_service

    async def classify(
        self,
        *,
        last_response: str,
        user_message: str,
        unresolved_targets: dict[str, str],
    ) -> ConfirmationFallbackDecision | None:
        if not unresolved_targets:
            return None

        allowed_fields = ", ".join(f"{field}={value}" for field, value in unresolved_targets.items())
        system_prompt = (
            "你是一个确认回复分类器。"
            "根据上一轮助手回复、当前用户回复、待确认字段和值，判断用户是否是在确认该候选值。"
            "只输出一行 JSON。"
            '确认时输出 {"result":"confirmed","field":"字段名"}。'
            '否认或纠正时输出 {"result":"denied","field":"字段名"}。'
            '不确定时输出 {"result":"unclear","field":""}。'
            f"本次只允许这些字段：{allowed_fields}。不要输出任何解释。"
        )
        prompt = (
            f"上一轮助手回复：{last_response}\n"
            f"当前用户回复：{user_message}\n"
            f"待确认字段：{allowed_fields}"
        )

        try:
            raw = await self.ai_service.generate_response(
                prompt,
                system_prompt,
                temperature=0.0,
                max_tokens=40,
                timeout=8.0,
            )
        except AIServiceException as exc:
            logger.warning("[confirmation_ai_fallback] failed: %s", exc)
            return None

        match = re.search(
            r'\{\s*"result"\s*:\s*"(?P<result>confirmed|denied|unclear)"\s*,\s*"field"\s*:\s*"(?P<field>[a-z_]*?)"\s*\}',
            str(raw or ""),
        )
        if not match:
            logger.info("[confirmation_ai_fallback] unparseable=%r", raw)
            return None

        return ConfirmationFallbackDecision(
            result=match.group("result"),
            field=match.group("field"),
        )
