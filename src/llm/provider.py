import os
from dataclasses import dataclass

from openai import AsyncOpenAI
from dotenv import load_dotenv


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
        )


class OpenAICompatibleLLM:
    def __init__(self, settings: LLMSettings | None = None):
        self.settings = settings or LLMSettings.from_env()
        self._client: AsyncOpenAI | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.api_key and self.settings.base_url and self.settings.model)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
                timeout=self.settings.timeout_seconds,
            )
        return self._client

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if not self.configured:
            return "I can help with that. Could you share a little more detail?"

        completion = await self._get_client().chat.completions.create(
            model=self.settings.model,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return completion.choices[0].message.content or ""
