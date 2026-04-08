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
        self.stale_job_ids = set()
        self.delivered = []

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

    async def is_outbox_job_stale(self, job):
        return job.job_id in self.stale_job_ids

    async def append_delivered_reply(self, account_id: str, reply_text: str, dialog_id=None, turn_id=None, now_ms=None):
        self.delivered.append((account_id, reply_text, dialog_id, turn_id))


class FailingDelivery:
    async def send_reply(self, account_id: str, reply_text: str, dialog_id=None, idempotency_key=None):
        raise RuntimeError("network error")


class RecordingDelivery:
    def __init__(self):
        self.calls = []

    async def send_reply(self, account_id: str, reply_text: str, dialog_id=None, idempotency_key=None):
        self.calls.append((account_id, reply_text, dialog_id, idempotency_key))


class FailOnceDelivery:
    def __init__(self):
        self.calls = []
        self.failed = False

    async def send_reply(self, account_id: str, reply_text: str, dialog_id=None, idempotency_key=None):
        self.calls.append((account_id, reply_text, dialog_id, idempotency_key))
        if not self.failed:
            self.failed = True
            raise RuntimeError("transient error")


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


def test_sender_drops_stale_job_before_delivery():
    asyncio.run(_test_sender_drops_stale_job_before_delivery())


async def _test_sender_drops_stale_job_before_delivery():
    job = OutboxJob(
        job_id="j_stale",
        account_id="u1",
        turn_id="t1",
        generation=1,
        reply_text="hello",
        dialog_id="d1",
        retry_count=0,
        next_retry_at_ms=int(time.time() * 1000),
    )
    store = DummyQueueStore([job])
    store.stale_job_ids.add("j_stale")
    delivery = RecordingDelivery()
    sender = ReplySenderWorker(
        queue_store=store,
        delivery_service=delivery,
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

    assert delivery.calls == []
    assert store.done == ["j_stale"]
    assert store.metrics.get("outbox_delivery_drop", 0) == 1
    assert store.metrics.get("stale_drop_count", 0) == 1


def test_sender_success_appends_delivered_reply_and_marks_done():
    asyncio.run(_test_sender_success_appends_delivered_reply_and_marks_done())


async def _test_sender_success_appends_delivered_reply_and_marks_done():
    job = OutboxJob(
        job_id="j_success",
        account_id="u1",
        turn_id="t_success",
        generation=1,
        reply_text="hello",
        dialog_id="d1",
        retry_count=0,
        next_retry_at_ms=int(time.time() * 1000),
    )
    store = DummyQueueStore([job])
    delivery = RecordingDelivery()
    sender = ReplySenderWorker(
        queue_store=store,
        delivery_service=delivery,
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

    assert delivery.calls == [("u1", "hello", "d1", "j_success")]
    assert store.delivered == [("u1", "hello", "d1", "t_success")]
    assert store.done == ["j_success"]
    assert store.metrics.get("outbox_delivery_success", 0) == 1


def test_sender_retries_then_succeeds_on_next_attempt():
    asyncio.run(_test_sender_retries_then_succeeds_on_next_attempt())


async def _test_sender_retries_then_succeeds_on_next_attempt():
    now_ms = int(time.time() * 1000)
    job = OutboxJob(
        job_id="j_retry_success",
        account_id="u1",
        turn_id="t_retry_success",
        generation=1,
        reply_text="hello",
        dialog_id="d1",
        retry_count=0,
        next_retry_at_ms=now_ms,
    )
    store = DummyQueueStore([job])
    delivery = FailOnceDelivery()
    sender = ReplySenderWorker(
        queue_store=store,
        delivery_service=delivery,
        batch_size=10,
        poll_ms=10,
        max_retries=3,
    )

    task = asyncio.create_task(sender.run_forever())
    await asyncio.sleep(0.05)

    assert len(store.retried) == 1
    retried = store.retried[0]
    retry_job = OutboxJob(
        job_id="j_retry_success",
        account_id="u1",
        turn_id="t_retry_success",
        generation=1,
        reply_text="hello",
        dialog_id="d1",
        retry_count=retried[1],
        next_retry_at_ms=retried[2],
    )
    store.jobs = [retry_job]

    await asyncio.sleep(0.05)
    sender.stop()
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(delivery.calls) >= 2
    assert store.delivered == [("u1", "hello", "d1", "t_retry_success")]
    assert store.done == ["j_retry_success"]
    assert store.metrics.get("outbox_delivery_retry", 0) == 1
    assert store.metrics.get("outbox_delivery_success", 0) == 1
