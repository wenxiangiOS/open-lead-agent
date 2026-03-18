import asyncio

from src.services.queue.reply_delivery_service import ReplyDeliveryService


class FakeReplyDeliveryService(ReplyDeliveryService):
    def __init__(self, primary: str = "", backup: str = "", fail_primary: bool = False):
        self.endpoint = primary
        self.backup_endpoint = backup
        self.timeout_seconds = 1.0
        self.fail_primary = fail_primary
        self.calls = []

    async def _deliver_to_endpoint(self, endpoint: str, payload: dict) -> None:
        self.calls.append(endpoint)
        if self.fail_primary and endpoint == self.endpoint:
            raise RuntimeError("primary failed")


def test_delivery_fallback_to_backup_endpoint():
    asyncio.run(_test_delivery_fallback_to_backup_endpoint())


async def _test_delivery_fallback_to_backup_endpoint():
    service = FakeReplyDeliveryService(
        primary="https://primary.example/send",
        backup="https://backup.example/send",
        fail_primary=True,
    )

    await service.send_reply(
        account_id="u1",
        reply_text="hello",
        dialog_id="d1",
        idempotency_key="job1",
    )

    assert service.calls == [
        "https://primary.example/send",
        "https://backup.example/send",
    ]


def test_delivery_skip_when_no_endpoint():
    asyncio.run(_test_delivery_skip_when_no_endpoint())


async def _test_delivery_skip_when_no_endpoint():
    service = FakeReplyDeliveryService(primary="", backup="")
    await service.send_reply(account_id="u1", reply_text="hello")
    assert service.calls == []
