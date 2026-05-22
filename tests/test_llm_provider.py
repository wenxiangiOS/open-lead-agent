import asyncio
from types import SimpleNamespace

from src.llm.provider import LLMSettings, OpenAICompatibleLLM


class FakeCompletions:
    async def create(self, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="你好呀"),
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=11,
                completion_tokens=3,
                total_tokens=14,
            ),
        )


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_llm_diagnostics_records_openai_compatible_usage():
    llm = OpenAICompatibleLLM(
        LLMSettings(
            provider="openai_compatible",
            api_key="key",
            model="demo",
            base_url="https://example.test",
            temperature=0.1,
            max_tokens=100,
            timeout_seconds=3,
            max_retries=0,
        )
    )
    llm._client = FakeClient()

    response = asyncio.run(llm.generate("system", "user"))

    diagnostics = llm.diagnostics()
    assert response == "你好呀"
    assert diagnostics["calls"] == 1
    assert diagnostics["input_tokens"] == 11
    assert diagnostics["output_tokens"] == 3
    assert diagnostics["total_tokens"] == 14
    assert diagnostics["details"][0]["route"] == "model"


def test_llm_diagnostics_records_unconfigured_fallback():
    llm = OpenAICompatibleLLM(
        LLMSettings(
            provider="openai_compatible",
            api_key="",
            model="",
            base_url="",
            temperature=0.1,
            max_tokens=100,
            timeout_seconds=3,
            max_retries=0,
        )
    )

    response = asyncio.run(llm.generate("system", "user"))

    diagnostics = llm.diagnostics()
    assert response
    assert diagnostics["calls"] == 1
    assert diagnostics["usage_available"] is False
    assert diagnostics["details"][0]["route"] == "unconfigured_fallback"
