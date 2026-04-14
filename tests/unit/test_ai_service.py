from unittest.mock import AsyncMock

import pytest

from src.services.ai_service import AIService, AIServiceException


class _FakeClient:
    async def close(self):
        return None


class _CreateRecorder:
    def __init__(self, content="ok"):
        self.calls = []
        self._content = content

    def _build_message(self):
        content = self._content

        class _Message:
            pass

        message = _Message()
        message.content = content
        return message

    async def create(self, **kwargs):
        self.calls.append(kwargs)

        class _Usage:
            prompt_tokens = 10
            completion_tokens = 20
            total_tokens = 30

        class _Choice:
            message = self._build_message()
            finish_reason = "stop"

        class _Response:
            id = "resp_test"
            usage = _Usage()
            choices = [_Choice()]

        return _Response()


class _RecordingClient:
    def __init__(self, content="ok"):
        self.recorder = _CreateRecorder(content=content)

        class _Completions:
            def __init__(self, recorder):
                self._recorder = recorder

            async def create(self, **kwargs):
                return await self._recorder.create(**kwargs)

        class _Chat:
            def __init__(self, recorder):
                self.completions = _Completions(recorder)

        self.chat = _Chat(self.recorder)

    async def close(self):
        return None


class _EmptyThenVisibleOutputClient:
    def __init__(self):
        self.calls = []

        class _Completions:
            def __init__(self, owner):
                self._owner = owner

            async def create(self, **kwargs):
                self._owner.calls.append(kwargs)
                call_index = len(self._owner.calls)

                class _Usage:
                    prompt_tokens = 10
                    completion_tokens = 20
                    total_tokens = 30

                class _Message:
                    pass

                message = _Message()

                class _Choice:
                    pass

                choice = _Choice()
                if call_index == 1:
                    message.content = ""
                    choice.finish_reason = "length"
                else:
                    message.content = "ok"
                    choice.finish_reason = "stop"
                choice.message = message

                class _Response:
                    id = f"resp_{call_index}"
                    usage = _Usage()
                    choices = [choice]

                return _Response()

        class _Chat:
            def __init__(self, owner):
                self.completions = _Completions(owner)

        self.chat = _Chat(self)

    async def close(self):
        return None


class _EmptyThenSlowFallbackClient:
    def __init__(self, fallback_sleep_seconds=0.2):
        self.calls = []
        self._fallback_sleep_seconds = fallback_sleep_seconds

        class _Completions:
            def __init__(self, owner):
                self._owner = owner

            async def create(self, **kwargs):
                import asyncio

                self._owner.calls.append(kwargs)
                call_index = len(self._owner.calls)

                class _Usage:
                    prompt_tokens = 10
                    completion_tokens = 20
                    total_tokens = 30

                class _Message:
                    pass

                message = _Message()

                class _Choice:
                    pass

                choice = _Choice()
                if call_index == 1:
                    message.content = ""
                    choice.finish_reason = "length"
                else:
                    await asyncio.sleep(self._owner._fallback_sleep_seconds)
                    message.content = "late"
                    choice.finish_reason = "stop"
                choice.message = message

                class _Response:
                    id = f"resp_{call_index}"
                    usage = _Usage()
                    choices = [choice]

                return _Response()

        class _Chat:
            def __init__(self, owner):
                self.completions = _Completions(owner)

        self.chat = _Chat(self)

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
async def test_generate_response_disable_retry_keeps_single_attempt_and_reports_no_retry(monkeypatch):
    monkeypatch.setenv("AI_CHAT_MAX_RETRIES", "3")
    service = AIService(client=_FakeClient())
    service._reset_client = AsyncMock(return_value=None)
    calls = {"count": 0}

    async def _slow(*args, **kwargs):
        calls["count"] += 1
        import asyncio
        await asyncio.sleep(0.05)
        return "never"

    service._do_generate_response = _slow

    with pytest.raises(AIServiceException) as exc_info:
        await service.generate_response("hi", "sys", timeout=0.01, disable_retry=True)

    assert "未重试" in str(exc_info.value)
    assert calls["count"] == 1
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


@pytest.mark.anyio
async def test_generate_response_prefers_max_completion_tokens_and_reasoning_effort():
    client = _RecordingClient()
    service = AIService(client=client)

    result = await service.generate_response(
        "hi",
        "sys",
        timeout=0.1,
        use_max_completion_tokens=True,
        reasoning_effort="minimal",
    )

    assert result == "ok"
    assert client.recorder.calls
    request = client.recorder.calls[0]
    assert request["max_completion_tokens"] == 500
    assert "max_tokens" not in request
    assert request["reasoning_effort"] == "minimal"


@pytest.mark.anyio
async def test_generate_response_extracts_text_from_structured_content_blocks():
    client = _RecordingClient(
        content=[
            {"type": "output_text", "text": "第一段"},
            {"type": "reasoning", "text": "内部推理"},
            {"type": "text", "text": "第二段"},
        ]
    )
    service = AIService(client=client)

    result = await service.generate_response("hi", "sys", timeout=0.1)

    assert result == "第一段\n第二段"


@pytest.mark.anyio
async def test_generate_response_empty_response_retries_without_resetting_client(monkeypatch):
    monkeypatch.setenv("AI_CHAT_MAX_RETRIES", "2")
    service = AIService(client=_FakeClient())
    service._reset_client = AsyncMock(return_value=None)
    calls = {"count": 0}

    async def _flaky(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise AIServiceException("AI 模型返回空响应", details={"reason": "empty_response"})
        return "ok"

    service._do_generate_response = _flaky

    result = await service.generate_response("hi", "sys", timeout=0.1)

    assert result == "ok"
    assert calls["count"] == 2
    service._reset_client.assert_not_awaited()


@pytest.mark.anyio
async def test_generate_response_retries_empty_length_response_with_max_tokens_fallback():
    client = _EmptyThenVisibleOutputClient()
    service = AIService(client=client)

    result = await service.generate_response(
        "hi",
        "sys",
        timeout=2.0,
        use_max_completion_tokens=True,
        reasoning_effort="low",
    )

    assert result == "ok"
    assert len(client.calls) == 2
    assert "max_completion_tokens" in client.calls[0]
    assert "max_tokens" not in client.calls[0]
    assert client.calls[1]["max_tokens"] == 500
    assert "max_completion_tokens" not in client.calls[1]
    assert "reasoning_effort" not in client.calls[1]


@pytest.mark.anyio
async def test_generate_response_empty_length_fallback_times_out_fast_without_turning_into_request_timeout(monkeypatch):
    monkeypatch.setenv("AI_EMPTY_RESPONSE_FALLBACK_TIMEOUT_SECONDS", "0.05")
    monkeypatch.setenv("AI_EMPTY_RESPONSE_FALLBACK_MIN_TIMEOUT_SECONDS", "0.01")
    monkeypatch.setenv("AI_EMPTY_RESPONSE_FALLBACK_SAFETY_MARGIN_SECONDS", "0")
    client = _EmptyThenSlowFallbackClient(fallback_sleep_seconds=0.2)
    service = AIService(client=client)
    service._reset_client = AsyncMock(return_value=None)

    with pytest.raises(AIServiceException) as exc_info:
        await service.generate_response(
            "hi",
            "sys",
            timeout=1.0,
            use_max_completion_tokens=True,
        )

    assert "空响应" in str(exc_info.value)
    assert "超时" not in str(exc_info.value)
    assert len(client.calls) == 2
    service._reset_client.assert_not_awaited()
