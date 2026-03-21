from types import SimpleNamespace

import pytest

from src.infrastructure.concurrency.rate_limiter import UnifiedRateLimiter


@pytest.mark.anyio
async def test_redis_mode_falls_back_to_memory_without_missing_helper(monkeypatch):
    limiter = UnifiedRateLimiter(use_redis=False, default_limit=2, default_window=60)
    limiter.use_redis = True

    fake_client = SimpleNamespace()
    monkeypatch.setattr("src.infrastructure.concurrency.rate_limiter.redis_service.client", fake_client)
    monkeypatch.setattr(
        "src.infrastructure.concurrency.rate_limiter.redis_service._key",
        lambda raw: f"ns:{raw}",
    )

    result = await limiter.is_allowed("user_1")

    assert result.allowed is True
    assert result.remaining == 1
    assert limiter._memory_store["user_1"]


def test_redis_key_helper_is_available_on_rate_limiter(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.concurrency.rate_limiter.redis_service._key",
        lambda raw: f"ns:{raw}",
    )

    assert UnifiedRateLimiter._redis_key("demo") == "ns:ratelimit:demo"
