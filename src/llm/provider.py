"""OpenAI-compatible 大模型配置与调用客户端。LLM settings and client."""

import os
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    api_key: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    max_retries: int

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "800")),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "0")),
        )


@dataclass
class LLMCallDiagnostic:
    route: str
    model: str
    input_chars: int
    output_chars: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    elapsed_ms: float = 0.0
    error: str = ""

    def public_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "model": self.model,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


@dataclass
class LLMDiagnostics:
    calls: list[LLMCallDiagnostic] = field(default_factory=list)

    def add(self, call: LLMCallDiagnostic) -> None:
        self.calls.append(call)

    def reset(self) -> None:
        self.calls.clear()

    def public_dict(self) -> dict[str, Any]:
        input_tokens = _sum_known(call.input_tokens for call in self.calls)
        output_tokens = _sum_known(call.output_tokens for call in self.calls)
        total_tokens = _sum_known(call.total_tokens for call in self.calls)
        estimated_input = sum(call.estimated_input_tokens for call in self.calls)
        estimated_output = sum(call.estimated_output_tokens for call in self.calls)
        return {
            "calls": len(self.calls),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_input_tokens": estimated_input,
            "estimated_output_tokens": estimated_output,
            "elapsed_ms": round(sum(call.elapsed_ms for call in self.calls), 2),
            "details": [call.public_dict() for call in self.calls],
            "usage_available": any(call.input_tokens is not None for call in self.calls),
        }


class OpenAICompatibleLLM:
    def __init__(self, settings: LLMSettings | None = None):
        self.settings = settings or LLMSettings.from_env()
        self._client: AsyncOpenAI | None = None
        self._diagnostics = LLMDiagnostics()

    @property
    def configured(self) -> bool:
        return bool(self.settings.api_key and self.settings.base_url and self.settings.model)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
                timeout=self.settings.timeout_seconds,
                max_retries=self.settings.max_retries,
            )
        return self._client

    def reset_diagnostics(self) -> None:
        self._diagnostics.reset()

    def diagnostics(self) -> dict[str, Any]:
        return self._diagnostics.public_dict()

    async def generate(self, system_prompt: str, user_message: str) -> str:
        started_at = perf_counter()
        input_chars = len(system_prompt) + len(user_message)
        if not self.configured:
            response = "I can help with that. Could you share a little more detail?"
            self._record_diagnostic(
                route="unconfigured_fallback",
                input_chars=input_chars,
                output=response,
                started_at=started_at,
            )
            return response

        try:
            completion = await self._get_client().chat.completions.create(
                model=self.settings.model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as exc:
            self._record_diagnostic(
                route="error",
                input_chars=input_chars,
                output="",
                started_at=started_at,
                error=str(exc) or exc.__class__.__name__,
            )
            raise

        response = completion.choices[0].message.content or ""
        usage = getattr(completion, "usage", None)
        self._record_diagnostic(
            route="model",
            input_chars=input_chars,
            output=response,
            started_at=started_at,
            input_tokens=_usage_value(usage, "prompt_tokens"),
            output_tokens=_usage_value(usage, "completion_tokens"),
            total_tokens=_usage_value(usage, "total_tokens"),
        )
        return response

    def _record_diagnostic(
        self,
        *,
        route: str,
        input_chars: int,
        output: str,
        started_at: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        error: str = "",
    ) -> None:
        self._diagnostics.add(
            LLMCallDiagnostic(
                route=route,
                model=self.settings.model,
                input_chars=input_chars,
                output_chars=len(output),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_input_tokens=_estimate_tokens(input_chars),
                estimated_output_tokens=_estimate_tokens(len(output)),
                elapsed_ms=round((perf_counter() - started_at) * 1000, 2),
                error=error,
            )
        )


def _usage_value(usage: Any, name: str) -> int | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        value = usage.get(name)
    else:
        value = getattr(usage, name, None)
    return value if isinstance(value, int) else None


def _sum_known(values: Any) -> int | None:
    known = [value for value in values if value is not None]
    if not known:
        return None
    return sum(known)


def _estimate_tokens(chars: int) -> int:
    if chars <= 0:
        return 0
    return max(1, round(chars / 4))
