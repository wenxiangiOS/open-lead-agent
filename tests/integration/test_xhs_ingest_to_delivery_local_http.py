import asyncio
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.api.routes.xiaohongshu_ingest import init_service as init_ingest_service, ingest_message
from src.services.data.redis_service import redis_service
from src.services.queue.message_orchestrator import MessageOrchestrator
from src.services.queue.queue_store import QueueStore
from src.services.queue.reply_delivery_service import ReplyDeliveryService
from src.workers.message_queue_worker import MessageQueueWorker
from src.workers.reply_sender_worker import ReplySenderWorker


class _CaptureHandler(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw)
        except Exception:
            body = {"_raw": raw}
        _CaptureHandler.received.append({"path": self.path, "body": body})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):  # noqa: A003
        return


class _DummyChatService:
    async def process_chat_request(self, request):
        return {
            "success": True,
            "response": f"已收到:{request.question}",
            "dialogId": request.dialogId,
        }


def _start_local_http_server():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    except PermissionError as exc:
        pytest.skip(f"local TCP bind not permitted in this environment: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_ingest_api_to_local_http_delivery_e2e():
    asyncio.run(_test_ingest_api_to_local_http_delivery_e2e())


async def _test_ingest_api_to_local_http_delivery_e2e():
    redis_service.enabled = False
    _CaptureHandler.received = []

    server, thread = _start_local_http_server()
    endpoint = f"http://127.0.0.1:{server.server_port}/xhs/reply"

    old_endpoint = os.environ.get("XHS_REPLY_API")
    os.environ["XHS_REPLY_API"] = endpoint

    try:
        store = QueueStore()
        orchestrator = MessageOrchestrator(chat_service=_DummyChatService(), queue_store=store)
        delivery = ReplyDeliveryService()
        mq_worker = MessageQueueWorker(orchestrator=orchestrator, queue_store=store, batch_size=20, poll_ms=10)
        sender_worker = ReplySenderWorker(queue_store=store, delivery_service=delivery, batch_size=20, poll_ms=10)

        init_ingest_service(orchestrator)

        # through ingest API route
        result = await ingest_message(
            {
                "accountId": "local_http_user",
                "dialogId": "d_local_http",
                "message": "第一条 好了",
                "platformMsgId": "local_http_1",
                "timestamp": "2026-03-18T12:00:00+08:00",
            }
        )
        assert result["success"] is True
        assert result["accepted"] is True

        t1 = asyncio.create_task(mq_worker.run_forever())
        t2 = asyncio.create_task(sender_worker.run_forever())

        # wait pipeline
        deadline = time.time() + 2.0
        while time.time() < deadline and not _CaptureHandler.received:
            await asyncio.sleep(0.02)

        mq_worker.stop()
        sender_worker.stop()
        await asyncio.sleep(0.05)
        t1.cancel()
        t2.cancel()
        await asyncio.gather(t1, t2, return_exceptions=True)

        assert len(_CaptureHandler.received) >= 1
        body = _CaptureHandler.received[0]["body"]
        assert body.get("accountId") == "local_http_user"
        assert body.get("dialogId") == "d_local_http"
        assert body.get("message")
        assert body.get("clientMsgId")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)
        if old_endpoint is None:
            os.environ.pop("XHS_REPLY_API", None)
        else:
            os.environ["XHS_REPLY_API"] = old_endpoint
