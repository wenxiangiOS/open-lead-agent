import asyncio

from src.modules.shared.models.use_case_models import (
    IngestMessageCommand,
    ProcessChatTurnCommand,
    ProcessChatTurnResult,
)
from src.services.data.redis_service import redis_service
from src.services.queue.message_orchestrator import MessageOrchestrator
from src.services.queue.queue_store import QueueStore


class DummyChatService:
    async def process_chat_request(self, request):
        return {
            "success": True,
            "response": "收到你的消息了",
            "dialogId": request.dialogId,
        }


class DummyChatServiceWithProtocol:
    def __init__(self):
        self.commands = []
        self.process_chat_turn_use_case = self

    async def execute_command(self, command):
        self.commands.append(command)
        return ProcessChatTurnResult(
            success=True,
            response="协议回复",
            dialog_id=command.dialog_id,
            payload={
                "success": True,
                "response": "协议回复",
                "dialogId": command.dialog_id,
            },
        )


def test_ingest_returns_queued():
    asyncio.run(_test_ingest_returns_queued())


async def _test_ingest_returns_queued():
    redis_service.enabled = False
    orchestrator = MessageOrchestrator(chat_service=DummyChatService(), queue_store=QueueStore())

    payload = {
        "accountId": "u2",
        "dialogId": "d2",
        "message": "你好",
        "platformMsgId": "pm2",
        "timestamp": "2026-03-18T00:00:00+08:00",
        "sex": "女",
    }
    result = await orchestrator.ingest(payload)
    assert result["success"] is True
    assert result["accepted"] is True
    assert result["status"] == "queued"


def test_combine_messages_keep_last():
    messages = [
        {"content": "第一句"},
        {"content": "第二句很长" * 1000},
        {"content": "最后补充"},
    ]
    out = MessageOrchestrator.combine_messages(messages, max_chars=20, keep_last_message=True)
    assert "最后补充" in out


def test_ingest_invalid_timestamp_is_tolerated_and_counted():
    asyncio.run(_test_ingest_invalid_timestamp_is_tolerated_and_counted())


async def _test_ingest_invalid_timestamp_is_tolerated_and_counted():
    redis_service.enabled = False
    store = QueueStore()
    orchestrator = MessageOrchestrator(chat_service=DummyChatService(), queue_store=store)

    payload = {
        "accountId": "u_ts",
        "dialogId": "d2",
        "message": "你好",
        "platformMsgId": "pm_ts_1",
        "timestamp": "not-a-time",
        "sex": "女",
    }
    result = await orchestrator.ingest(payload)
    assert result["success"] is True
    assert result["accepted"] is True

    stats = await store.get_queue_metrics()
    assert stats["invalid_timestamp_count"] == 1



def test_ingest_metrics_counting():
    asyncio.run(_test_ingest_metrics_counting())


async def _test_ingest_metrics_counting():
    redis_service.enabled = False
    store = QueueStore()
    orchestrator = MessageOrchestrator(chat_service=DummyChatService(), queue_store=store)

    result1 = await orchestrator.ingest({"accountId": "", "platformMsgId": "x", "message": "hi"})
    result2 = await orchestrator.ingest({"accountId": "u3", "platformMsgId": "x2", "message": ""})
    result3 = await orchestrator.ingest({
        "accountId": "u3",
        "dialogId": "d3",
        "message": "你好",
        "platformMsgId": "pm3",
    })

    assert result1["status"] == "invalid_payload"
    assert result2["status"] == "ignored_empty"
    assert result3["status"] == "queued"

    metrics = await store.get_queue_metrics()
    assert metrics["ingest_total"] == 3
    assert metrics["ingest_invalid_payload"] == 1
    assert metrics["ingest_ignored_empty"] == 1
    assert metrics["ingest_accepted"] == 1



class EmptyChatService:
    async def process_chat_request(self, request):
        return {"success": True, "response": "", "dialogId": request.dialogId}


def test_empty_response_business_silent_metric():
    asyncio.run(_test_empty_response_business_silent_metric())


async def _test_empty_response_business_silent_metric():
    redis_service.enabled = False
    store = QueueStore()
    orchestrator = MessageOrchestrator(chat_service=EmptyChatService(), queue_store=store)

    now_payload = {
        "accountId": "u_empty",
        "dialogId": "d_empty",
        "message": "第一句 好了",
        "platformMsgId": "pm_empty_1",
    }
    await orchestrator.ingest(now_payload)
    await orchestrator.run_user_turn("u_empty")

    metrics = await store.get_queue_metrics()
    assert metrics["empty_response_business_silent"] >= 1


def test_combine_messages_context_compaction():
    messages = [
        {"content": "开头信息"},
        {"content": "中间非常非常长的信息1"},
        {"content": "中间非常非常长的信息2"},
        {"content": "最后补充"},
    ]
    out = MessageOrchestrator.combine_messages(
        messages,
        max_chars=28,
        keep_last_message=True,
        compact_middle=True,
    )
    assert "最后补充" in out
    assert "省略" in out


def test_ingest_command_returns_result_object():
    asyncio.run(_test_ingest_command_returns_result_object())


async def _test_ingest_command_returns_result_object():
    redis_service.enabled = False
    orchestrator = MessageOrchestrator(chat_service=DummyChatService(), queue_store=QueueStore())

    result = await orchestrator.ingest_command(
        IngestMessageCommand(
            account_id="u_cmd",
            dialog_id="d_cmd",
            message="你好",
            platform_msg_id="pm_cmd",
            timestamp="2026-03-18T00:00:00+08:00",
            sex="女",
        )
    )

    assert result.success is True
    assert result.accepted is True
    assert result.status == "queued"


def test_process_turn_command_prefers_process_chat_turn_command_protocol():
    asyncio.run(_test_process_turn_command_prefers_process_chat_turn_command_protocol())


async def _test_process_turn_command_prefers_process_chat_turn_command_protocol():
    redis_service.enabled = False
    chat_service = DummyChatServiceWithProtocol()
    store = QueueStore()
    orchestrator = MessageOrchestrator(chat_service=chat_service, queue_store=store)

    result = await orchestrator._process_turn_command(  # noqa: SLF001
        ProcessChatTurnCommand(
            question="第一句",
            account_id="u_protocol_turn",
            dialog_id="d_protocol_turn",
            sex="女",
            timestamp="2026-03-18T00:00:00+08:00",
        )
    )

    assert len(chat_service.commands) == 1
    command = chat_service.commands[0]
    assert command.account_id == "u_protocol_turn"
    assert command.dialog_id == "d_protocol_turn"
    assert result.response == "协议回复"
