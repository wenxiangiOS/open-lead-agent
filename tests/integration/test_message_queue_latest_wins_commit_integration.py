import asyncio
import os
import time

from src.models.user_profile import UserProfile
from src.services.data.redis_service import redis_service
from src.services.data.user_service import UserService
from src.services.queue.message_orchestrator import MessageOrchestrator
from src.services.queue.queue_store import QueueStore
from src.services.queue.turn_commit_service import TurnCommitService
from src.workers.reply_sender_worker import ReplySenderWorker


class _RecordingDelivery:
    def __init__(self):
        self.calls = []

    async def send_reply(self, account_id: str, reply_text: str, dialog_id=None, idempotency_key=None):
        self.calls.append((account_id, reply_text, dialog_id, idempotency_key))


class _MutatingChatService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.questions = []

    async def process_chat_request(self, request):
        self.questions.append(request.question)
        profile = await self.user_service.get_user_profile(request.accountId)
        profile.last_name = f"marker:{request.question}"
        await self.user_service.save_user_profile(request.accountId, profile)
        return {
            "success": True,
            "response": f"R:{request.question}",
            "dialogId": request.dialogId,
        }


class _SilentMutatingChatService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def process_chat_request(self, request):
        profile = await self.user_service.get_user_profile(request.accountId)
        profile.last_name = "should_not_commit"
        await self.user_service.save_user_profile(request.accountId, profile)
        return {
            "success": True,
            "response": "",
            "dialogId": request.dialogId,
        }


async def _run_sender_until(sender: ReplySenderWorker, done_check, timeout_seconds: float = 3.0) -> None:
    task = asyncio.create_task(sender.run_forever())
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            if done_check():
                return
            await asyncio.sleep(0.02)
        raise AssertionError("sender worker did not finish within timeout")
    finally:
        sender.stop()
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_latest_wins_sender_only_delivers_and_commits_last_turn():
    asyncio.run(_test_latest_wins_sender_only_delivers_and_commits_last_turn())


async def _test_latest_wins_sender_only_delivers_and_commits_last_turn():
    redis_service.enabled = False
    previous_force = os.environ.get("MQ_FORCE_FLUSH_ENABLED")
    os.environ["MQ_FORCE_FLUSH_ENABLED"] = "true"
    try:
        store = QueueStore()
        user_service = UserService()
        chat_service = _MutatingChatService(user_service)
        commit_service = TurnCommitService(user_service=user_service, queue_store=store)
        orchestrator = MessageOrchestrator(chat_service=chat_service, queue_store=store, commit_service=commit_service)
        delivery = _RecordingDelivery()
        sender = ReplySenderWorker(
            queue_store=store,
            delivery_service=delivery,
            commit_service=commit_service,
            batch_size=20,
            poll_ms=10,
        )

        account_id = "latest_wins_user"
        dialog_id = "d_latest"
        conversation_key = QueueStore.conversation_key(account_id, dialog_id)

        # turn-1: 先生成候选 outbox，但先不发送
        await orchestrator.ingest(
            {
                "accountId": account_id,
                "dialogId": dialog_id,
                "message": "第一条消息 好了",
                "platformMsgId": "lw_1",
                "timestamp": "2026-04-13T10:00:00+08:00",
            }
        )
        await orchestrator.run_user_turn(account_id)

        # turn-2: 新输入覆盖旧候选，形成最新候选
        await orchestrator.ingest(
            {
                "accountId": account_id,
                "dialogId": dialog_id,
                "message": "第二条补充 好了",
                "platformMsgId": "lw_2",
                "timestamp": "2026-04-13T10:00:01+08:00",
            }
        )
        await orchestrator.run_user_turn(account_id)

        jobs = list(store._memory_outbox.values())  # noqa: SLF001
        assert len(jobs) == 2
        job_by_seq = {int(job.covered_end_seq): job for job in jobs}
        assert 1 in job_by_seq and 2 in job_by_seq

        await _run_sender_until(
            sender,
            done_check=lambda: (len(store._memory_outbox) == 0 and len(delivery.calls) >= 1),  # noqa: SLF001
        )

        assert len(delivery.calls) == 1
        sent = delivery.calls[0]
        assert sent[0] == account_id
        assert sent[2] == dialog_id
        assert sent[1] == "R:第一条消息 好了\n第二条补充 好了"
        assert "第二条补充" in sent[1]

        # 仅最后 turn 被提交
        assert await store.is_turn_committed(job_by_seq[1].turn_id) is False
        assert await store.is_turn_committed(job_by_seq[2].turn_id) is True

        profile = await user_service.get_user_profile(account_id)
        assert isinstance(profile, UserProfile)
        assert profile.last_name == "marker:第一条消息 好了\n第二条补充 好了"

        session = await store.get_session(conversation_key)
        assert session.last_ack_seq == 2
        assert session.max_enqueued_seq == 2
        assert session.pending_turn_id == ""

        metrics = await store.get_queue_metrics()
        assert metrics["outbox_delivery_success"] >= 1
        assert metrics["outbox_delivery_drop"] >= 1
        assert metrics["stale_drop_count"] >= 1
    finally:
        if previous_force is None:
            os.environ.pop("MQ_FORCE_FLUSH_ENABLED", None)
        else:
            os.environ["MQ_FORCE_FLUSH_ENABLED"] = previous_force


def test_silent_branch_rechecks_stale_before_commit():
    asyncio.run(_test_silent_branch_rechecks_stale_before_commit())


async def _test_silent_branch_rechecks_stale_before_commit():
    redis_service.enabled = False
    previous_force = os.environ.get("MQ_FORCE_FLUSH_ENABLED")
    os.environ["MQ_FORCE_FLUSH_ENABLED"] = "true"
    try:
        store = QueueStore()
        user_service = UserService()
        chat_service = _SilentMutatingChatService(user_service)
        commit_service = TurnCommitService(user_service=user_service, queue_store=store)
        orchestrator = MessageOrchestrator(chat_service=chat_service, queue_store=store, commit_service=commit_service)

        await orchestrator.ingest(
            {
                "accountId": "silent_stale_user",
                "dialogId": "d_silent",
                "message": "这条会被覆盖 好了",
                "platformMsgId": "silent_stale_1",
                "timestamp": "2026-04-13T10:01:00+08:00",
            }
        )

        stale_checks = {"count": 0}

        async def _stale_after_first_check(turn):  # noqa: ARG001
            stale_checks["count"] += 1
            return stale_checks["count"] >= 2

        store.is_turn_stale = _stale_after_first_check  # type: ignore[assignment]

        await orchestrator.run_user_turn("silent_stale_user")

        assert stale_checks["count"] >= 2
        profile = await user_service.get_user_profile("silent_stale_user")
        assert profile.last_name is None
        assert len(store._memory_committed_turns) == 0  # noqa: SLF001

        metrics = await store.get_queue_metrics()
        assert metrics["turn_stale"] >= 1
    finally:
        if previous_force is None:
            os.environ.pop("MQ_FORCE_FLUSH_ENABLED", None)
        else:
            os.environ["MQ_FORCE_FLUSH_ENABLED"] = previous_force
