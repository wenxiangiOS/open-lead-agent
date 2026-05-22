"""理解层 JSON 解析。

兼容新的 observations 结构，也兼容旧的扁平字段 JSON，方便平滑迁移。
"""

import json
from typing import Any

from src.understanding.models import FieldObservation, TurnSemanticFrame


class UnderstandingParser:
    def parse(self, raw_response: str) -> TurnSemanticFrame:
        parsed = self._parse_json_object(raw_response)
        if not parsed:
            return TurnSemanticFrame(confidence=0.0)

        observations = self._parse_observations(parsed)
        return TurnSemanticFrame(
            intents=self._string_list(parsed.get("intents")),
            observations=observations,
            turn_mode=str(parsed.get("turn_mode") or "default"),
            no_reask_fields=self._string_list(parsed.get("no_reask_fields")),
            faq_intent=self._optional_string(parsed.get("faq_intent")),
            compliance_signals=self._string_list(parsed.get("compliance_signals")),
            reply_act=str(parsed.get("reply_act") or "continue"),
            confidence=self._float_or_default(parsed.get("confidence"), 1.0),
            raw_payload=parsed,
        )

    def _parse_json_object(self, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        if text.startswith("```"):
            text = self._strip_code_fence(text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        nested = parsed.get("collected")
        if isinstance(nested, dict):
            return nested
        return parsed

    def _parse_observations(self, parsed: dict[str, Any]) -> list[FieldObservation]:
        raw_observations = parsed.get("observations")
        if isinstance(raw_observations, list):
            return [
                observation
                for item in raw_observations
                if isinstance(item, dict)
                for observation in [self._observation_from_dict(item)]
                if observation is not None
            ]
        reserved = {
            "intents",
            "observations",
            "turn_mode",
            "no_reask_fields",
            "faq_intent",
            "compliance_signals",
            "reply_act",
            "confidence",
            "contact_intent",
            "concern",
            "refusal",
        }
        return [
            FieldObservation(field=key, value=value, source="llm")
            for key, value in parsed.items()
            if key not in reserved
        ]

    def _observation_from_dict(self, item: dict[str, Any]) -> FieldObservation | None:
        field = str(item.get("field") or item.get("key") or "").strip()
        if not field:
            return None
        return FieldObservation(
            field=field,
            value=item.get("value"),
            normalized_value=item.get("normalized_value"),
            scope=str(item.get("scope") or "self"),
            owner=str(item.get("owner") or "user"),
            evidence_text=str(item.get("evidence_text") or ""),
            confidence=self._float_or_default(item.get("confidence"), 1.0),
            write_mode=str(item.get("write_mode") or "direct_write"),
            source=str(item.get("source") or "llm"),
            reason=str(item.get("reason") or ""),
        )

    def _strip_code_fence(self, text: str) -> str:
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _optional_string(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _float_or_default(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
