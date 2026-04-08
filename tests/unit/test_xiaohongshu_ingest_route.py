import asyncio

from starlette.requests import Request

from src.api.routes import xiaohongshu_ingest as ingest_routes
from src.modules.shared.models.use_case_models import IngestMessageResult


class _StubOrchestrator:
    def __init__(self):
        self.commands = []
        self.queue_store = None

    async def ingest_command(self, command):
        self.commands.append(command)
        return IngestMessageResult(
            success=True,
            accepted=True,
            status="queued",
            session_state="pending",
            seq=1,
            pending=1,
            max_pending=20,
            cancel_like=False,
            force_flush=False,
            payload={
                "success": True,
                "accepted": True,
                "status": "queued",
                "sessionState": "pending",
                "seq": 1,
                "pending": 1,
                "maxPending": 20,
                "cancelLike": False,
                "forceFlush": False,
            },
        )


def test_ingest_route_builds_ingest_command_protocol():
    asyncio.run(_test_ingest_route_builds_ingest_command_protocol())


async def _test_ingest_route_builds_ingest_command_protocol():
    stub = _StubOrchestrator()
    original = ingest_routes.orchestrator
    try:
        ingest_routes.orchestrator = stub
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/xiaohongshu/messages/ingest",
                "headers": [],
            }
        )
        payload = {
            "accountId": "xhs_user_1",
            "dialogId": "xhs_dialog_1",
            "message": "你好",
            "platformMsgId": "xhs_msg_1",
            "timestamp": "2026-03-18T00:00:00+08:00",
            "sex": "女",
        }

        result = await ingest_routes.ingest_message(request, payload)

        assert result["success"] is True
        assert result["status"] == "queued"
        assert len(stub.commands) == 1
        assert stub.commands[0].account_id == "xhs_user_1"
        assert stub.commands[0].platform_msg_id == "xhs_msg_1"
    finally:
        ingest_routes.orchestrator = original


def test_poll_replies_returns_delivered_receipts():
    asyncio.run(_test_poll_replies_returns_delivered_receipts())


async def _test_poll_replies_returns_delivered_receipts():
    class _StubQueueStore:
        async def fetch_delivered_replies(self, account_id: str, after_id: int = 0, limit: int = 20):
            assert account_id == "xhs_user_1"
            assert after_id == 10
            assert limit == 2
            return [
                {"id": 11, "accountId": account_id, "message": "第一条"},
                {"id": 12, "accountId": account_id, "message": "第二条"},
            ]

    stub = _StubOrchestrator()
    stub.queue_store = _StubQueueStore()
    original = ingest_routes.orchestrator
    try:
        ingest_routes.orchestrator = stub
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/xiaohongshu/messages/replies",
                "headers": [],
                "query_string": b"accountId=xhs_user_1&after=10&limit=2",
            }
        )

        result = await ingest_routes.poll_replies(request, accountId="xhs_user_1", after=10, limit=2)

        assert result["success"] is True
        assert result["after"] == 10
        assert result["nextAfter"] == 12
        assert [item["message"] for item in result["replies"]] == ["第一条", "第二条"]
    finally:
        ingest_routes.orchestrator = original


def test_stream_replies_emits_replies_event():
    asyncio.run(_test_stream_replies_emits_replies_event())


async def _test_stream_replies_emits_replies_event():
    class _StubQueueStore:
        async def fetch_delivered_replies(self, account_id: str, after_id: int = 0, limit: int = 20):
            return [
                {"id": 21, "accountId": account_id, "message": "流式第一条"},
            ]

    stub = _StubOrchestrator()
    stub.queue_store = _StubQueueStore()
    original = ingest_routes.orchestrator
    try:
        ingest_routes.orchestrator = stub
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/xiaohongshu/messages/replies/stream",
                "headers": [],
                "query_string": b"accountId=xhs_user_1&after=0&limit=20",
            }
        )
        request.is_disconnected = lambda: asyncio.sleep(0, result=False)  # type: ignore[method-assign]

        response = await ingest_routes.stream_replies(request, accountId="xhs_user_1", after=0, limit=20)
        chunk = await response.body_iterator.__anext__()
        await response.body_iterator.aclose()

        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        assert "event: replies" in text
        assert "流式第一条" in text
        assert "\"nextAfter\": 21" in text
    finally:
        ingest_routes.orchestrator = original
