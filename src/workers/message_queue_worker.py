from __future__ import annotations

import asyncio
import logging
import time

from src.modules.message_queue.application.message_orchestrator import MessageOrchestrator
from src.modules.message_queue.infrastructure.queue_store import QueueStore
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MessageQueueWorker:
    def __init__(
        self,
        orchestrator: MessageOrchestrator,
        queue_store: QueueStore,
        batch_size: int = 100,
        poll_ms: int = 100,
        user_concurrency: int = 4,
    ) -> None:
        self.orchestrator = orchestrator
        self.queue_store = queue_store
        self.batch_size = batch_size
        self.poll_ms = poll_ms
        self.user_concurrency = max(1, int(user_concurrency))
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def _split_hot_users(self, user_ids: list[str]) -> tuple[list[str], list[str]]:
        hot_threshold = int(getattr(settings, "mq_hot_user_pending_threshold", 8))
        normal_users: list[str] = []
        hot_users: list[str] = []

        for account_id in user_ids:
            try:
                session = await self.queue_store.get_session(account_id)
                pending = max(0, int(session.max_enqueued_seq) - int(session.last_consumed_seq))
                if pending >= hot_threshold:
                    hot_users.append(account_id)
                else:
                    normal_users.append(account_id)
            except Exception:
                normal_users.append(account_id)

        return normal_users, hot_users

    async def run_forever(self) -> None:
        logger.info("[mq.worker] started")
        last_recovery_ms = 0
        recovery_interval_ms = int(getattr(settings, "mq_recovery_interval_ms", 5000))
        while not self._stop_event.is_set():
            now_ms = int(time.time() * 1000)
            try:
                if now_ms - last_recovery_ms >= recovery_interval_ms:
                    stale_after_ms = int(getattr(settings, "mq_running_stale_after_ms", 120000))
                    recovery_batch = int(getattr(settings, "mq_recovery_batch_size", 200))
                    await self.queue_store.recover_stale_running_sessions(now_ms, stale_after_ms, limit=recovery_batch)
                    last_recovery_ms = now_ms

                user_ids = await self.queue_store.fetch_ready_users(now_ms, limit=self.batch_size)
                if not user_ids:
                    await asyncio.sleep(self.poll_ms / 1000)
                    continue

                normal_users, hot_users = await self._split_hot_users(user_ids)
                hot_quota = int(getattr(settings, "mq_hot_user_quota_per_loop", 2))
                deferred_hot = hot_users[hot_quota:]
                if deferred_hot:
                    reschedule_ms = now_ms + int(getattr(settings, "mq_hot_user_reschedule_ms", 100))
                    for uid in deferred_hot:
                        await self.queue_store.schedule_user(uid, reschedule_ms)

                process_list = normal_users + hot_users[:hot_quota]
                sem = asyncio.Semaphore(self.user_concurrency)

                async def _run_one(account_id: str) -> None:
                    async with sem:
                        if self._stop_event.is_set():
                            return
                        try:
                            await self.orchestrator.run_user_turn(account_id)
                        except Exception:
                            logger.exception("[mq.worker] run_user_turn failed", extra={"account_id": account_id})

                if process_list:
                    await asyncio.gather(*[_run_one(account_id) for account_id in process_list])
            except Exception:
                logger.exception("[mq.worker] loop error")
                await asyncio.sleep(self.poll_ms / 1000)
        logger.info("[mq.worker] stopped")
