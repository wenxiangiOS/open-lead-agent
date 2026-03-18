import asyncio
import time

from src.services.queue.message_models import OutboxJob
from src.workers.reply_sender_worker import ReplySenderWorker


class DummyQueueStore:
    def __init__(self, jobs):
        self.jobs = jobs
        self.retried = []
        self.done = []
        self.metrics = {}

    async def fetch_due_outbox_jobs(self, now_ms: int, limit: int = 100):
        if self.jobs:
            jobs = self.jobs[:]
            self.jobs = []
            return jobs
        return []

    async def retry_outbox(self, job_id: str, retry_count: int, next_retry_at_ms: int, error: str):
        self.retried.append((job_id, retry_count, next_retry_at_ms, error))

    async def mark_outbox_done(self, job_id: str):
        self.done.append(job_id)

    async def incr_metric(self, name: str, value: int = 1):
        self.metrics[name] = self.metrics.get(name, 0) + value


class FailingDelivery:
    async def send_reply(self, account_id: str, reply_text: str, dialog_id=None, idempotency_key=None):
        raise RuntimeError("network error")


def test_sender_retry_on_failure():
    asyncio.run(_test_sender_retry_on_failure())


async def _test_sender_retry_on_failure():
    job = OutboxJob(
        job_id="j1",
        account_id="u1",
        turn_id="t1",
        generation=1,
        reply_text="hello",
        dialog_id="d1",
        retry_count=0,
        next_retry_at_ms=int(time.time() * 1000),
    )
    store = DummyQueueStore([job])
    sender = ReplySenderWorker(
        queue_store=store,
        delivery_service=FailingDelivery(),
        batch_size=10,
        poll_ms=10,
        max_retries=3,
    )

    task = asyncio.create_task(sender.run_forever())
    await asyncio.sleep(0.05)
    sender.stop()
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(store.retried) == 1
    assert store.retried[0][0] == "j1"
    assert store.retried[0][1] == 1
    assert store.done == []
    assert store.metrics.get("outbox_delivery_retry", 0) == 1
