from unittest.mock import AsyncMock

import pytest

from src.services.ai_service import AIService, AIServiceException


class _FakeClient:
    async def close(self):
        return None


@pytest.mark.anyio
async def test_generate_response_resets_client_on_timeout():
    service = AIService(client=_FakeClient())
    service._reset_client = AsyncMock(return_value=None)

    async def _slow(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.05)
        return "never"

    service._do_generate_response = _slow

    with pytest.raises(AIServiceException):
        await service.generate_response("hi", "sys", timeout=0.01)

    service._reset_client.assert_awaited()


@pytest.mark.anyio
async def test_generate_response_resets_client_on_generic_error():
    service = AIService(client=_FakeClient())
    service._reset_client = AsyncMock(return_value=None)

    async def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    service._do_generate_response = _boom

    with pytest.raises(AIServiceException):
        await service.generate_response("hi", "sys", timeout=0.1)

    service._reset_client.assert_awaited()


def test_resolve_timeout_settings_derives_from_chat_ai_timeout(monkeypatch):
    monkeypatch.delenv("AI_HTTP_TOTAL_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("CHAT_AI_HARD_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("CONCURRENCY_REQUEST_TIMEOUT", raising=False)
    monkeypatch.setenv("CHAT_AI_TIMEOUT_SECONDS", "80")

    settings = AIService.resolve_timeout_settings()

    assert settings["chat_ai_timeout"] == 80
    assert settings["http_total_timeout"] == 85
    assert settings["chat_ai_hard_timeout"] == 90
    assert settings["request_timeout"] == 100
