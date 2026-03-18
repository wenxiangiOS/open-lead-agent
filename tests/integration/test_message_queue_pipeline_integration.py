import asyncio
import time

from src.services.data.redis_service import redis_service
from src.services.queue.message_orchestrator import MessageOrchestrator
from src.services.queue.queue_store import QueueStore
from src.workers.message_queue_worker import MessageQueueWorker


class EchoChatService:
    def __init__(self):
        self.questions = []

    async def process_chat_request(self, request):
        self.questions.append(request.question)
        return {
            "success": True,
            "response": f"ECHO:{request.question}",
            "dialogId": request.dialogId,
        }


class SlowFirstTurnChatService:
    def __init__(self):
        self.questions = []
        self.first_call_started = asyncio.Event()
        self.release_first_call = asyncio.Event()
        self.call_count = 0

    async def process_chat_request(self, request):
        self.call_count += 1
        self.questions.append(request.question)

        if self.call_count == 1:
            self.first_call_started.set()
            await self.release_first_call.wait()

        return {
            "success": True,
            "response": f"ECHO:{request.question}",
            "dialogId": request.dialogId,
        }


async def _run_worker_for(worker: MessageQueueWorker, seconds: float) -> None:
    task = asyncio.create_task(worker.run_forever())
    await asyncio.sleep(seconds)
    worker.stop()
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def test_burst_messages_not_lost_and_in_order():
    asyncio.run(_test_burst_messages_not_lost_and_in_order())


async def _test_burst_messages_not_lost_and_in_order():
    redis_service.enabled = False

    store = QueueStore()
    chat = EchoChatService()
    orchestrator = MessageOrchestrator(chat_service=chat, queue_store=store)
    worker = MessageQueueWorker(orchestrator=orchestrator, queue_store=store, batch_size=20, poll_ms=10)

    account_id = "it_burst_user"
    for idx in range(1, 6):
        payload = {
            "accountId": account_id,
            "dialogId": "d_burst",
            "message": f"第{idx}条",
            "platformMsgId": f"burst_{idx}",
            "timestamp": "2026-03-18T12:00:00+08:00",
        }
        result = await orchestrator.ingest(payload)
        assert result["accepted"] is True

    # trigger immediate run
    await orchestrator.ingest(
        {
            "accountId": account_id,
            "dialogId": "d_burst",
            "message": "好了",
            "platformMsgId": "burst_flush",
            "timestamp": "2026-03-18T12:00:01+08:00",
        }
    )

    await _run_worker_for(worker, 0.4)

    session = await store.get_session(account_id)
    assert session.last_consumed_seq >= 6
    assert session.max_enqueued_seq >= 6

    assert len(chat.questions) >= 1
    combined = "\n".join(chat.questions)
    assert "第1条" in combined
    assert "第5条" in combined
    assert combined.index("第1条") < combined.index("第5条")


def test_cancel_drops_stale_reply():
    asyncio.run(_test_cancel_drops_stale_reply())


async def _test_cancel_drops_stale_reply():
    redis_service.enabled = False

    store = QueueStore()
    chat = SlowFirstTurnChatService()
    orchestrator = MessageOrchestrator(chat_service=chat, queue_store=store)
    worker = MessageQueueWorker(orchestrator=orchestrator, queue_store=store, batch_size=20, poll_ms=10)

    worker_task = asyncio.create_task(worker.run_forever())

    account_id = "it_cancel_user"
    await orchestrator.ingest(
        {
            "accountId": account_id,
            "dialogId": "d_cancel",
            "message": "第一条消息 好了",
            "platformMsgId": "cancel_1",
            "timestamp": "2026-03-18T12:01:00+08:00",
        }
    )

    await asyncio.wait_for(chat.first_call_started.wait(), timeout=1.0)

    # cancel-like message arrives while first turn is running
    await orchestrator.ingest(
        {
            "accountId": account_id,
            "dialogId": "d_cancel",
            "message": "算了 好了",
            "platformMsgId": "cancel_2",
            "timestamp": "2026-03-18T12:01:02+08:00",
        }
    )

    # release old turn response; it should be stale-dropped
    chat.release_first_call.set()

    await asyncio.sleep(0.5)
    worker.stop()
    await asyncio.sleep(0.05)
    worker_task.cancel()
    await asyncio.gather(worker_task, return_exceptions=True)

    # Outbox should only contain non-stale turn reply
    jobs = list(store._memory_outbox.values())  # noqa: SLF001
    assert len(jobs) == 1
    assert "算了" in jobs[0].reply_text
    assert "第一条消息" not in jobs[0].reply_text

    metrics = await store.get_queue_metrics()
    assert metrics["stale_drop_count"] >= 1


def test_worker_restart_can_resume_pending_messages():
    asyncio.run(_test_worker_restart_can_resume_pending_messages())


async def _test_worker_restart_can_resume_pending_messages():
    redis_service.enabled = False

    store = QueueStore()
    chat = EchoChatService()
    orchestrator = MessageOrchestrator(chat_service=chat, queue_store=store)

    account_id = "it_restart_user"
    await orchestrator.ingest(
        {
            "accountId": account_id,
            "dialogId": "d_restart",
            "message": "重启前入队 好了",
            "platformMsgId": "restart_1",
            "timestamp": "2026-03-18T12:02:00+08:00",
        }
    )

    # simulate worker not running for a while
    await asyncio.sleep(0.05)

    worker = MessageQueueWorker(orchestrator=orchestrator, queue_store=store, batch_size=20, poll_ms=10)
    await _run_worker_for(worker, 0.3)

    session = await store.get_session(account_id)
    assert session.last_consumed_seq >= 1
    assert len(chat.questions) >= 1
