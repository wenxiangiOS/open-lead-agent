#!/usr/bin/env python3
"""P0 production smoke runner for message queue pipeline.

Purpose:
- validate ingest -> queue worker -> sender -> external delivery endpoint
- generate a markdown evidence report for final P0 sign-off
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.data.redis_service import redis_service
from src.services.queue.message_orchestrator import MessageOrchestrator
from src.services.queue.queue_store import QueueStore
from src.services.queue.reply_delivery_service import ReplyDeliveryService
from src.workers.message_queue_worker import MessageQueueWorker
from src.workers.reply_sender_worker import ReplySenderWorker


class _SmokeChatService:
    async def process_chat_request(self, request):
        return {
            "success": True,
            "response": f"[mq-smoke]{request.question}",
            "dialogId": request.dialogId,
        }


def _write_report(report_file: Path, status: str, endpoint: str, account_id: str, dialog_id: str, metrics: dict, notes: str) -> None:
    report_file.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat()
    content = [
        "# P0 Production Smoke Report",
        "",
        f"- GeneratedAt: {now}",
        f"- Status: {status}",
        f"- Endpoint: {endpoint or '(empty)'}",
        f"- AccountId: {account_id}",
        f"- DialogId: {dialog_id}",
        f"- Notes: {notes}",
        "",
        "## Metrics Snapshot",
        "",
        "```json",
        str(metrics).replace("'", '"'),
        "```",
        "",
    ]
    report_file.write_text("\n".join(content), encoding="utf-8")


async def _run_once(timeout_seconds: float, account_id: str, dialog_id: str, report_file: Path) -> int:
    endpoint = (os.getenv("XHS_REPLY_API") or "").strip()

    if os.getenv("REDIS_ENABLED", "").strip().lower() in ("0", "false", "no", "off"):
        redis_service.enabled = False

    if not endpoint:
        msg = "XHS_REPLY_API is empty; cannot run production delivery smoke"
        print(f"[SKIP] {msg}")
        _write_report(report_file, "SKIP", endpoint, account_id, dialog_id, {}, msg)
        return 2

    store = QueueStore()
    orchestrator = MessageOrchestrator(chat_service=_SmokeChatService(), queue_store=store)
    delivery = ReplyDeliveryService()
    mq_worker = MessageQueueWorker(orchestrator=orchestrator, queue_store=store, batch_size=20, poll_ms=10)
    sender_worker = ReplySenderWorker(queue_store=store, delivery_service=delivery, batch_size=20, poll_ms=10)

    payload = {
        "accountId": account_id,
        "dialogId": dialog_id,
        "message": "生产联调smoke 好了",
        "platformMsgId": f"mq-smoke-{uuid.uuid4().hex[:16]}",
        "timestamp": "2026-03-18T12:00:00+08:00",
    }

    ingest = await orchestrator.ingest(payload)
    if not ingest.get("accepted"):
        print(f"[FAIL] ingest not accepted: {ingest}")
        metrics = await store.get_queue_metrics()
        _write_report(report_file, "FAIL", endpoint, account_id, dialog_id, metrics, f"ingest not accepted: {ingest}")
        return 1

    t1 = asyncio.create_task(mq_worker.run_forever(), name="smoke_mq_worker")
    t2 = asyncio.create_task(sender_worker.run_forever(), name="smoke_sender_worker")

    deadline = time.time() + timeout_seconds
    success = False
    last_metrics = {}

    try:
        while time.time() < deadline:
            metrics = await store.get_queue_metrics()
            last_metrics = metrics
            if int(metrics.get("outbox_delivery_success", 0)) >= 1:
                success = True
                break
            await asyncio.sleep(0.05)
    finally:
        mq_worker.stop()
        sender_worker.stop()
        await asyncio.sleep(0.05)
        t1.cancel()
        t2.cancel()
        await asyncio.gather(t1, t2, return_exceptions=True)

    if success:
        print("[PASS] production smoke finished")
        print(f"endpoint={endpoint}")
        print(f"metrics={last_metrics}")
        _write_report(report_file, "PASS", endpoint, account_id, dialog_id, last_metrics, "outbox_delivery_success >= 1")
        return 0

    print("[FAIL] timeout waiting for outbox_delivery_success >= 1")
    print(f"endpoint={endpoint}")
    print(f"metrics={last_metrics}")
    _write_report(report_file, "FAIL", endpoint, account_id, dialog_id, last_metrics, "timeout waiting for outbox_delivery_success >= 1")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MQ P0 production smoke validation")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--account-id", default=f"mq_smoke_{int(time.time())}")
    parser.add_argument("--dialog-id", default=f"d_smoke_{int(time.time())}")
    parser.add_argument("--report-file", default="reports/mq/p0_production_smoke_latest.md")
    args = parser.parse_args()

    report_file = Path(args.report_file)
    if not report_file.is_absolute():
        report_file = ROOT / report_file

    rc = asyncio.run(_run_once(args.timeout_seconds, args.account_id, args.dialog_id, report_file))
    print(f"report={report_file}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
