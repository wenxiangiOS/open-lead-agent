from __future__ import annotations

import asyncio
import logging
import time

from src.modules.message_queue.infrastructure.queue_store import QueueStore
from src.modules.message_queue.infrastructure.reply_delivery_service import ReplyDeliveryService

logger = logging.getLogger(__name__)


def _next_retry_delay_seconds(retry_count: int) -> int:
    table = [5, 15, 30, 60]
    if retry_count <= 0:
        return table[0]
    if retry_count <= len(table):
        return table[retry_count - 1]
    return 300


class ReplySenderWorker:
    def __init__(
        self,
        queue_store: QueueStore,
        delivery_service: ReplyDeliveryService,
        batch_size: int = 100,
        poll_ms: int = 500,
        max_retries: int = 8,
        job_concurrency: int = 8,
    ) -> None:
        self.queue_store = queue_store
        self.delivery_service = delivery_service
        self.batch_size = batch_size
        self.poll_ms = poll_ms
        self.max_retries = max_retries
        self.job_concurrency = max(1, int(job_concurrency))
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def _incr_metric(self, name: str, value: int = 1) -> None:
        if not hasattr(self.queue_store, "incr_metric"):
            return
        try:
            await self.queue_store.incr_metric(name, value)
        except Exception:
            logger.debug("[mq.metrics] sender incr failed", extra={"metric": name})

    async def run_forever(self) -> None:
        logger.info("[mq.sender] started")
        while not self._stop_event.is_set():
            now_ms = int(time.time() * 1000)
            try:
                jobs = await self.queue_store.fetch_due_outbox_jobs(now_ms, limit=self.batch_size)
                if not jobs:
                    await asyncio.sleep(self.poll_ms / 1000)
                    continue

                sem = asyncio.Semaphore(self.job_concurrency)

                async def _handle_job(job) -> None:
                    async with sem:
                        if self._stop_event.is_set():
                            return
                        try:
                            if hasattr(self.queue_store, "is_outbox_job_stale") and await self.queue_store.is_outbox_job_stale(job):
                                logger.info(
                                    "[mq.sender] stale outbox job dropped",
                                    extra={"job_id": job.job_id, "account_id": job.account_id, "generation": job.generation},
                                )
                                await self.queue_store.mark_outbox_done(job.job_id)
                                await self._incr_metric("outbox_delivery_drop")
                                await self._incr_metric("stale_drop_count")
                                return
                            await self.delivery_service.send_reply(
                                account_id=job.account_id,
                                reply_text=job.reply_text,
                                dialog_id=job.dialog_id,
                                idempotency_key=job.job_id,
                            )
                            await self.queue_store.append_delivered_reply(
                                account_id=job.account_id,
                                reply_text=job.reply_text,
                                dialog_id=job.dialog_id,
                                turn_id=job.turn_id,
                                now_ms=int(time.time() * 1000),
                            )
                            await self.queue_store.mark_outbox_done(job.job_id)
                            await self._incr_metric("outbox_delivery_success")
                        except Exception as exc:
                            retry_count = job.retry_count + 1
                            if retry_count > self.max_retries:
                                logger.error(
                                    "[mq.sender] drop job after max retries",
                                    extra={"job_id": job.job_id, "account_id": job.account_id, "error": str(exc)},
                                )
                                await self.queue_store.mark_outbox_done(job.job_id)
                                await self._incr_metric("outbox_delivery_drop")
                                return

                            delay = _next_retry_delay_seconds(retry_count)
                            next_retry_at_ms = int(time.time() * 1000) + delay * 1000
                            await self.queue_store.retry_outbox(job.job_id, retry_count, next_retry_at_ms, str(exc))
                            await self._incr_metric("outbox_delivery_retry")

                if jobs:
                    await asyncio.gather(*[_handle_job(job) for job in jobs])
            except Exception:
                logger.exception("[mq.sender] loop error")
                await asyncio.sleep(self.poll_ms / 1000)
        logger.info("[mq.sender] stopped")
