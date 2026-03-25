import pytest

from src.api.routes import system


class _DummyQueueStore:
    async def get_queue_metrics(self):
        return {
            "ingest_total": 10,
            "ingest_accepted": 8,
            "outbox_created": 4,
            "outbox_delivery_success": 3,
            "turn_started": 5,
            "turn_succeeded": 4,
            "contact_validation_retry": 3,
            "contact_validation_silent": 1,
        }


def test_safe_rate_handles_zero_denominator():
    assert system._safe_rate(1, 0) == 0.0  # noqa: SLF001


@pytest.mark.anyio
async def test_message_queue_dashboard_includes_validation_breakdown():
    original = system.queue_store
    try:
        system.queue_store = _DummyQueueStore()
        payload = await system.get_message_queue_dashboard()
    finally:
        system.queue_store = original

    dashboard = payload["dashboard"]
    assert dashboard["validation"]["retry_count"] == 3
    assert dashboard["validation"]["silent_count"] == 1
    assert dashboard["validation"]["total"] == 4
    assert dashboard["ratios"]["contact_validation_retry_share"] == 0.75
    assert dashboard["ratios"]["contact_validation_silent_share"] == 0.25
