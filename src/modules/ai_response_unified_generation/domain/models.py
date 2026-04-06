from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIGenerationDraft:
    raw_ai_response: str
    generation_source: str = "ai"
    response_plan_id: str | None = None


@dataclass
class AIResponseValidationResult:
    delivery_status: str
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    should_fallback: bool = False
    fallback_reason: str | None = None


@dataclass
class AIDisplayResponse:
    display_response: str
    raw_ai_response: str
    safe_cleaned: bool
    fallback_used: bool
    fallback_reason: str | None = None
