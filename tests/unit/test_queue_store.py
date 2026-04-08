import asyncio
import json
import time

from src.services.data.redis_service import redis_service
from src.services.queue.message_models import IncomingMessage, OutboxJob
from src.services.queue.queue_store import QueueStore


def test_enqueue_and_turn_flow_memory_mode():
    asyncio.run(_test_enqueue_and_turn_flow_memory_mode())


def test_queue_ttl_supports_duration_strings():
    store = QueueStore()
    store._cfg = lambda name, default: {  # type: ignore[assignment]
        "mq_session_ttl_seconds": "7d",
        "mq_dedupe_ttl_seconds": "24h",
    }.get(name, default)

    assert store._session_ttl() == 604800
    assert store._dedupe_ttl() == 86400


async def _test_enqueue_and_turn_flow_memory_mode():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    msg = IncomingMessage(
        account_id="u1",
        dialog_id="d1",
        content="你好",
        platform_msg_id="m1",
        timestamp="2026-03-18T00:00:00+08:00",
    )
    result = await store.enqueue_message(msg, now_ms)
    assert result.accepted is True
    assert result.duplicate is False

    session = await store.get_session("u1")
    assert session.max_enqueued_seq == 1

    # force ready and start turn
    await store.schedule_user("u1", now_ms)
    turn = await store.start_turn("u1", now_ms + 2000)
    assert turn is not None
    assert turn.start_seq == 1
    assert turn.end_seq == 1

    msgs = await store.get_turn_messages("u1", turn.start_seq, turn.end_seq)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "你好"

    await store.finish_turn_success("u1", turn, now_ms + 3000, has_more=False)
    session = await store.get_session("u1")
    assert session.state == "IDLE"


def test_enqueue_duplicate_memory_mode():
    asyncio.run(_test_enqueue_duplicate_memory_mode())


async def _test_enqueue_duplicate_memory_mode():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    msg = IncomingMessage(
        account_id="u_dedupe",
        dialog_id="d1",
        content="你好",
        platform_msg_id="dup_1",
        timestamp="2026-03-18T00:00:00+08:00",
    )

    first = await store.enqueue_message(msg, now_ms)
    second = await store.enqueue_message(msg, now_ms + 10)

    assert first.accepted is True
    assert first.duplicate is False
    assert second.accepted is False
    assert second.duplicate is True
    assert second.status == "duplicate"

    session = await store.get_session("u_dedupe")
    assert session.max_enqueued_seq == 1


def test_enqueue_queue_full_memory_mode():
    asyncio.run(_test_enqueue_queue_full_memory_mode())


async def _test_enqueue_queue_full_memory_mode():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    # preset a full pending window: max_enqueued_seq - last_consumed_seq = 20
    session = await store.get_session("u_full")
    session.last_consumed_seq = 0
    session.max_enqueued_seq = 20
    store._memory_sessions["u_full"] = session  # noqa: SLF001

    msg = IncomingMessage(
        account_id="u_full",
        dialog_id="d1",
        content="新消息",
        platform_msg_id="full_m1",
        timestamp="2026-03-18T00:00:00+08:00",
    )
    result = await store.enqueue_message(msg, now_ms)
    assert result.accepted is False
    assert result.status == "queue_full"


def test_mark_turn_failed_circuit_breaker_and_success_reset():
    asyncio.run(_test_mark_turn_failed_circuit_breaker_and_success_reset())


async def _test_mark_turn_failed_circuit_breaker_and_success_reset():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    # prepare one message and start a running turn
    msg = IncomingMessage(
        account_id="u_fail",
        dialog_id="d1",
        content="你好",
        platform_msg_id="m_fail_1",
        timestamp="2026-03-18T00:00:00+08:00",
    )
    await store.enqueue_message(msg, now_ms)
    turn = await store.start_turn("u_fail", now_ms + 2000)
    assert turn is not None

    await store.mark_turn_failed("u_fail", turn, now_ms + 2100)
    session = await store.get_session("u_fail")
    assert session.fail_streak == 1
    assert session.state == "DEBOUNCING"

    await store.mark_turn_failed("u_fail", turn, now_ms + 2200)
    await store.mark_turn_failed("u_fail", turn, now_ms + 2300)
    session = await store.get_session("u_fail")
    assert session.fail_streak >= 3
    # after crossing threshold, next schedule should be noticeably larger than recheck 300ms
    assert session.debounce_until_ms - (now_ms + 2300) >= 5000

    await store.finish_turn_success("u_fail", turn, now_ms + 2400, has_more=False)
    session = await store.get_session("u_fail")
    assert session.fail_streak == 0


def test_recover_stale_running_sessions_respects_limit():
    asyncio.run(_test_recover_stale_running_sessions_respects_limit())


async def _test_recover_stale_running_sessions_respects_limit():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    for idx in range(5):
        account_id = f"u_stale_{idx}"
        session = await store.get_session(account_id)
        session.state = "RUNNING"
        session.updated_at_ms = now_ms - 999999
        store._memory_sessions[account_id] = session  # noqa: SLF001

    recovered = await store.recover_stale_running_sessions(now_ms, stale_after_ms=1000, limit=2)
    assert recovered == 2

    recovered_states = [
        s.state for s in store._memory_sessions.values() if s.account_id.startswith("u_stale_")  # noqa: SLF001
    ]
    assert recovered_states.count("DEBOUNCING") == 2


def test_priority_boost_for_cancel_like_memory_mode():
    asyncio.run(_test_priority_boost_for_cancel_like_memory_mode())


async def _test_priority_boost_for_cancel_like_memory_mode():
    redis_service.enabled = False
    store = QueueStore()
    now_ms = int(time.time() * 1000)

    msg = IncomingMessage(
        account_id="u_pri",
        dialog_id="d_pri",
        content="算了先这样",
        platform_msg_id="m_pri_1",
        timestamp="2026-03-18T00:00:00+08:00",
        cancel_like=True,
        force_flush=False,
    )
    result = await store.enqueue_message(msg, now_ms)
    assert result.accepted is True

    session = await store.get_session("u_pri")
    score = store._memory_ready["u_pri"]  # noqa: SLF001
    assert session.debounce_until_ms - score >= 200


def test_adaptive_debounce_memory_mode():
    asyncio.run(_test_adaptive_debounce_memory_mode())


async def _test_adaptive_debounce_memory_mode():
    redis_service.enabled = False
    store = QueueStore()

    def cfg(name: str, default):
        if name == "mq_adaptive_debounce_enabled":
            return True
        return default

    store._cfg = cfg  # type: ignore[assignment]

    now_ms = int(time.time() * 1000)
    session = await store.get_session("u_adapt")
    session.updated_at_ms = now_ms - 500
    store._memory_sessions["u_adapt"] = session  # noqa: SLF001

    msg = IncomingMessage(
        account_id="u_adapt",
        dialog_id="d1",
        content="普通消息",
        platform_msg_id="adapt_1",
        timestamp="2026-03-18T00:00:00+08:00",
    )
    await store.enqueue_message(msg, now_ms)

    session2 = await store.get_session("u_adapt")
    # gap=500ms => adaptive debounce about 300ms instead of default 1000ms
    assert 250 <= (session2.debounce_until_ms - now_ms) <= 500


def test_get_queue_metrics_redis_scan_path_no_name_error():
    asyncio.run(_test_get_queue_metrics_redis_scan_path_no_name_error())


async def _test_get_queue_metrics_redis_scan_path_no_name_error():
    store = QueueStore()

    class FakeClient:
        async def zcard(self, _key):
            return 1

        async def scan_iter(self, match=None, count=200):
            yield "mq:session:u_redis_1"

        async def get(self, key):
            if key == "mq:session:u_redis_1":
                return json.dumps({
                    "state": "DEBOUNCING",
                    "max_enqueued_seq": 3,
                    "last_consumed_seq": 1,
                })
            return "0"

    async def fake_get_client():
        return FakeClient()

    store._get_client = fake_get_client  # type: ignore[assignment]
    store._key = lambda key: key  # type: ignore[assignment]
    metrics = await store.get_queue_metrics()
    assert metrics["pending_depth"] == 2
    assert metrics["debouncing_sessions"] == 1


def test_is_outbox_job_stale_when_generation_changes():
    asyncio.run(_test_is_outbox_job_stale_when_generation_changes())


async def _test_is_outbox_job_stale_when_generation_changes():
    redis_service.enabled = False
    store = QueueStore()
    session = await store.get_session("u_outbox_stale")
    session.generation = 2
    store._memory_sessions["u_outbox_stale"] = session  # noqa: SLF001

    job = OutboxJob(
        job_id="j_stale",
        account_id="u_outbox_stale",
        turn_id="t1",
        generation=1,
        reply_text="旧回复",
        dialog_id="d1",
        retry_count=0,
        next_retry_at_ms=int(time.time() * 1000),
    )

    assert await store.is_outbox_job_stale(job) is True


def test_acquire_and_release_user_lock_redis_path():
    asyncio.run(_test_acquire_and_release_user_lock_redis_path())


async def _test_acquire_and_release_user_lock_redis_path():
    store = QueueStore()

    class FakeClient:
        def __init__(self):
            self.values = {}

        async def set(self, key, value, ex=None, nx=False):
            if nx and key in self.values:
                return False
            self.values[key] = value
            return True

        async def eval(self, script, numkeys, key, token):
            if self.values.get(key) == token:
                self.values.pop(key, None)
                return 1
            return 0

    client = FakeClient()

    async def fake_get_client():
        return client

    store._get_client = fake_get_client  # type: ignore[assignment]
    store._key = lambda key: key  # type: ignore[assignment]

    locked = await store.acquire_user_lock("u_lock", "token_a", ttl_seconds=30)
    assert locked is True

    locked_again = await store.acquire_user_lock("u_lock", "token_b", ttl_seconds=30)
    assert locked_again is False

    await store.release_user_lock("u_lock", "token_b")
    assert client.values["lock:mq:user:u_lock"] == "token_a"

    await store.release_user_lock("u_lock", "token_a")
    assert "lock:mq:user:u_lock" not in client.values
