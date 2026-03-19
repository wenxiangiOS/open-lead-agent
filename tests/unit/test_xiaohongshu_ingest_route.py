import asyncio

from starlette.requests import Request

from src.api.routes import xiaohongshu_ingest as ingest_routes
from src.modules.shared.models.use_case_models import IngestMessageResult


class _StubOrchestrator:
    def __init__(self):
        self.commands = []

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
