import asyncio
from types import SimpleNamespace

from src.workers.message_queue_worker import MessageQueueWorker


class DummyStore:
    def __init__(self):
        self.recover_calls = []
        self.ready_calls = 0
        self.scheduled = []
        self.pending_map = {}

    async def recover_stale_running_sessions(self, now_ms: int, stale_after_ms: int, limit: int = 200):
        self.recover_calls.append((now_ms, stale_after_ms, limit))
        return 0

    async def fetch_ready_users(self, now_ms: int, limit: int = 100):
        self.ready_calls += 1
        return []

    async def get_session(self, account_id: str):
        pending = self.pending_map.get(account_id, 0)
        return SimpleNamespace(last_consumed_seq=0, max_enqueued_seq=pending)

    async def schedule_user(self, account_id: str, run_at_ms: int):
        self.scheduled.append((account_id, run_at_ms))


class DummyOrchestrator:
    def __init__(self):
        self.calls = []

    async def run_user_turn(self, account_id: str):
        self.calls.append(account_id)
        return None


def test_worker_runs_recovery_before_fetching_ready_users():
    asyncio.run(_test_worker_runs_recovery_before_fetching_ready_users())


async def _test_worker_runs_recovery_before_fetching_ready_users():
    store = DummyStore()
    worker = MessageQueueWorker(
        orchestrator=DummyOrchestrator(),
        queue_store=store,
        batch_size=10,
        poll_ms=10,
    )

    task = asyncio.create_task(worker.run_forever())
    await asyncio.sleep(0.05)
    worker.stop()
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert store.ready_calls > 0
    assert len(store.recover_calls) > 0
    assert store.recover_calls[0][1] == 120000
    assert store.recover_calls[0][2] == 200


def test_hot_user_isolation_reschedules_excess_hot_users():
    asyncio.run(_test_hot_user_isolation_reschedules_excess_hot_users())


async def _test_hot_user_isolation_reschedules_excess_hot_users():
    store = DummyStore()
    orchestrator = DummyOrchestrator()

    # one normal + three hot users
    user_order = ["normal_u", "hot_u1", "hot_u2", "hot_u3"]
    store.pending_map = {
        "normal_u": 1,
        "hot_u1": 20,
        "hot_u2": 18,
        "hot_u3": 15,
    }

    async def fetch_once(now_ms: int, limit: int = 100):
        if store.ready_calls == 0:
            store.ready_calls += 1
            return user_order
        store.ready_calls += 1
        return []

    store.fetch_ready_users = fetch_once

    worker = MessageQueueWorker(
        orchestrator=orchestrator,
        queue_store=store,
        batch_size=10,
        poll_ms=10,
    )

    task = asyncio.create_task(worker.run_forever())
    await asyncio.sleep(0.08)
    worker.stop()
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # default hot quota is 2 -> normal + first two hot processed, one hot deferred
    assert orchestrator.calls[0] == "normal_u"
    assert "hot_u1" in orchestrator.calls
    assert "hot_u2" in orchestrator.calls
    assert "hot_u3" not in orchestrator.calls
    assert any(uid == "hot_u3" for uid, _ in store.scheduled)
