import asyncio
import os

from src.api import app as app_module


def test_startup_does_not_spawn_mq_workers_when_disabled(monkeypatch):
    asyncio.run(_test_startup_does_not_spawn_mq_workers_when_disabled(monkeypatch))


async def _test_startup_does_not_spawn_mq_workers_when_disabled(monkeypatch):
    prev = os.getenv("MQ_ENABLED")
    os.environ["MQ_ENABLED"] = "false"

    async def _noop_cleanup():
        return None

    monkeypatch.setattr(app_module, "validate_config_on_startup", lambda _settings: None)
    monkeypatch.setattr(app_module, "async_cleanup_resources", _noop_cleanup)

    for task in list(app_module.worker_tasks):
        task.cancel()
    if app_module.worker_tasks:
        await asyncio.gather(*app_module.worker_tasks, return_exceptions=True)
        app_module.worker_tasks.clear()

    try:
        await app_module.startup_event()
        assert app_module.worker_tasks == []
    finally:
        await app_module.shutdown_event()
        if prev is None:
            os.environ.pop("MQ_ENABLED", None)
        else:
            os.environ["MQ_ENABLED"] = prev
