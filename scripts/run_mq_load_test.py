#!/usr/bin/env python3
"""Simple concurrent load test for MQ ingest API."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RequestResult:
    account_id: str
    msg_index: int
    latency_ms: float
    http_status: int
    ok: bool
    ingest_status: str
    accepted: bool
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MQ ingest 并发压测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="服务地址")
    parser.add_argument("--api-key", default="", help="可选 X-API-Key")
    parser.add_argument("--accounts", type=int, default=20, help="账号数")
    parser.add_argument("--messages-per-account", type=int, default=10, help="每账号消息数")
    parser.add_argument("--concurrency", type=int, default=20, help="并发 worker 数")
    parser.add_argument("--timeout-seconds", type=float, default=8.0, help="单请求超时秒数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--message-prefix", default="mq_load", help="消息前缀")
    parser.add_argument("--jitter-ms", type=int, default=0, help="请求前随机抖动毫秒")
    parser.add_argument("--include-dashboard", action="store_true", help="采集压测前后 dashboard")
    parser.add_argument("--report-json", default="", help="报告输出路径（默认写入 reports/mq_load）")
    parser.add_argument("--gate", action="store_true", help="开启门禁阈值检查，不达标返回非 0")
    parser.add_argument("--max-fail-rate", type=float, default=0.02, help="门禁：最大失败率（默认 0.02）")
    parser.add_argument("--max-p95-ms", type=float, default=400.0, help="门禁：p95 最大时延 ms（默认 400）")
    parser.add_argument("--max-p99-ms", type=float, default=800.0, help="门禁：p99 最大时延 ms（默认 800）")
    parser.add_argument("--max-latency-ms", type=float, default=3000.0, help="门禁：单请求最大时延 ms（默认 3000）")
    parser.add_argument("--min-rps", type=float, default=1.0, help="门禁：最小吞吐 rps（默认 1.0）")
    parser.add_argument("--max-queue-full-rate", type=float, default=0.5, help="门禁：queue_full 最大占比（默认 0.5）")
    parser.add_argument("--verbose", action="store_true", help="打印失败明细")
    return parser.parse_args()


def _http_json(method: str, url: str, payload: dict[str, Any] | None, headers: dict[str, str], timeout_seconds: float) -> tuple[int, dict[str, Any]]:
    body = None
    req_headers = dict(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = resp.read().decode("utf-8")
            return int(resp.status), json.loads(data) if data else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp is not None else ""
        try:
            return int(exc.code), json.loads(raw) if raw else {}
        except Exception:
            return int(exc.code), {"detail": raw or str(exc)}


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    pos = (len(sorted_values) - 1) * p
    low = int(pos)
    high = min(low + 1, len(sorted_values) - 1)
    if low == high:
        return sorted_values[low]
    ratio = pos - low
    return sorted_values[low] * (1.0 - ratio) + sorted_values[high] * ratio


def _build_payload(account_id: str, msg_index: int, run_id: str, message_prefix: str) -> dict[str, Any]:
    return {
        "accountId": account_id,
        "dialogId": f"mq_load_{account_id}_{run_id}",
        "message": f"{message_prefix} msg#{msg_index}",
        "platformMsgId": f"mq_load_{account_id}_{msg_index}_{run_id}",
        "timestamp": str(int(time.time() * 1000)),
    }


def _fetch_dashboard(base_url: str, headers: dict[str, str], timeout_seconds: float) -> dict[str, Any]:
    dashboard_url = f"{base_url.rstrip('/')}/api/doubao/mq/dashboard"
    status, body = _http_json("GET", dashboard_url, None, headers, timeout_seconds)
    return {"http_status": status, "body": body}


def main() -> int:
    args = parse_args()
    random.seed(args.seed)

    run_id = uuid.uuid4().hex[:8]
    ingest_url = f"{args.base_url.rstrip('/')}/api/xiaohongshu/messages/ingest"
    headers: dict[str, str] = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    accounts = [f"mq_load_acc_{i}_{run_id}" for i in range(1, args.accounts + 1)]
    tasks: list[tuple[str, int]] = []
    for account_id in accounts:
        for msg_index in range(1, args.messages_per_account + 1):
            tasks.append((account_id, msg_index))

    random.shuffle(tasks)

    dashboard_before: dict[str, Any] | None = None
    dashboard_after: dict[str, Any] | None = None
    if args.include_dashboard:
        dashboard_before = _fetch_dashboard(args.base_url, headers, args.timeout_seconds)

    lock = threading.Lock()
    started_at = time.time()
    results: list[RequestResult] = []

    def _send_one(task: tuple[str, int]) -> RequestResult:
        account_id, msg_index = task
        if args.jitter_ms > 0:
            time.sleep(random.randint(0, args.jitter_ms) / 1000.0)
        payload = _build_payload(account_id, msg_index, run_id, args.message_prefix)
        t0 = time.time()
        try:
            http_status, body = _http_json("POST", ingest_url, payload, headers, args.timeout_seconds)
            latency_ms = (time.time() - t0) * 1000.0
            ok = http_status == 200
            ingest_status = str(body.get("status", "")) if isinstance(body, dict) else ""
            accepted = bool(body.get("accepted", False)) if isinstance(body, dict) else False
            error = ""
            if not ok:
                error = f"http_status={http_status}, body={body}"
            return RequestResult(
                account_id=account_id,
                msg_index=msg_index,
                latency_ms=latency_ms,
                http_status=http_status,
                ok=ok,
                ingest_status=ingest_status,
                accepted=accepted,
                error=error,
            )
        except Exception as exc:
            latency_ms = (time.time() - t0) * 1000.0
            return RequestResult(
                account_id=account_id,
                msg_index=msg_index,
                latency_ms=latency_ms,
                http_status=0,
                ok=False,
                ingest_status="request_error",
                accepted=False,
                error=str(exc),
            )

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [pool.submit(_send_one, task) for task in tasks]
        for fut in as_completed(futures):
            res = fut.result()
            with lock:
                results.append(res)

    total_duration = time.time() - started_at

    if args.include_dashboard:
        dashboard_after = _fetch_dashboard(args.base_url, headers, args.timeout_seconds)

    total = len(results)
    success = sum(1 for r in results if r.ok)
    failed = total - success
    accepted = sum(1 for r in results if r.accepted)
    queued = sum(1 for r in results if r.ingest_status == "queued")
    duplicate = sum(1 for r in results if r.ingest_status == "duplicate")
    queue_full = sum(1 for r in results if r.ingest_status == "queue_full")
    invalid_payload = sum(1 for r in results if r.ingest_status == "invalid_payload")
    ignored_empty = sum(1 for r in results if r.ingest_status == "ignored_empty")

    latencies = [r.latency_ms for r in results]
    rps = total / total_duration if total_duration > 0 else 0.0

    summary = {
        "run_id": run_id,
        "base_url": args.base_url,
        "accounts": args.accounts,
        "messages_per_account": args.messages_per_account,
        "concurrency": args.concurrency,
        "total_requests": total,
        "http_success": success,
        "http_failed": failed,
        "accepted": accepted,
        "queued": queued,
        "duplicate": duplicate,
        "queue_full": queue_full,
        "invalid_payload": invalid_payload,
        "ignored_empty": ignored_empty,
        "duration_seconds": round(total_duration, 3),
        "rps": round(rps, 2),
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50": round(_percentile(latencies, 0.50), 2),
            "p90": round(_percentile(latencies, 0.90), 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "p99": round(_percentile(latencies, 0.99), 2),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "dashboard_before": dashboard_before,
        "dashboard_after": dashboard_after,
        "timestamp": datetime.now().isoformat(),
    }

    print("=== MQ Load Test Summary ===")
    print(f"total_requests: {summary['total_requests']}")
    print(f"http_success: {summary['http_success']}")
    print(f"http_failed: {summary['http_failed']}")
    print(f"accepted: {summary['accepted']}")
    print(f"queued/duplicate/queue_full: {queued}/{duplicate}/{queue_full}")
    print(f"duration: {summary['duration_seconds']}s, rps: {summary['rps']}")
    print(
        "latency_ms: "
        f"avg={summary['latency_ms']['avg']} "
        f"p50={summary['latency_ms']['p50']} "
        f"p90={summary['latency_ms']['p90']} "
        f"p95={summary['latency_ms']['p95']} "
        f"p99={summary['latency_ms']['p99']} "
        f"max={summary['latency_ms']['max']}"
    )

    if args.verbose and failed > 0:
        print("\n=== Failures ===")
        shown = 0
        for item in results:
            if item.ok:
                continue
            print(
                f"account={item.account_id} msg={item.msg_index} "
                f"http={item.http_status} status={item.ingest_status} error={item.error}"
            )
            shown += 1
            if shown >= 20:
                break

    gate_passed = True
    gate_reasons: list[str] = []
    fail_rate = (failed / total) if total > 0 else 1.0
    queue_full_rate = (queue_full / total) if total > 0 else 0.0
    p95 = float(summary["latency_ms"]["p95"])
    p99 = float(summary["latency_ms"]["p99"])
    max_latency = float(summary["latency_ms"]["max"])
    rps_value = float(summary["rps"])

    if args.gate:
        if fail_rate > args.max_fail_rate:
            gate_passed = False
            gate_reasons.append(f"fail_rate={fail_rate:.4f} > {args.max_fail_rate:.4f}")
        if p95 > args.max_p95_ms:
            gate_passed = False
            gate_reasons.append(f"p95={p95:.2f}ms > {args.max_p95_ms:.2f}ms")
        if p99 > args.max_p99_ms:
            gate_passed = False
            gate_reasons.append(f"p99={p99:.2f}ms > {args.max_p99_ms:.2f}ms")
        if max_latency > args.max_latency_ms:
            gate_passed = False
            gate_reasons.append(f"max={max_latency:.2f}ms > {args.max_latency_ms:.2f}ms")
        if rps_value < args.min_rps:
            gate_passed = False
            gate_reasons.append(f"rps={rps_value:.2f} < {args.min_rps:.2f}")
        if queue_full_rate > args.max_queue_full_rate:
            gate_passed = False
            gate_reasons.append(f"queue_full_rate={queue_full_rate:.4f} > {args.max_queue_full_rate:.4f}")

        print("\n=== Gate Result ===")
        print(f"gate_passed: {gate_passed}")
        if gate_reasons:
            for reason in gate_reasons:
                print(f"- {reason}")

    report_path: Path
    if args.report_json:
        report_path = Path(args.report_json)
    else:
        report_dir = PROJECT_ROOT / "reports" / "mq_load"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"mq_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "gate": {
                    "enabled": bool(args.gate),
                    "passed": gate_passed,
                    "thresholds": {
                        "max_fail_rate": args.max_fail_rate,
                        "max_p95_ms": args.max_p95_ms,
                        "max_p99_ms": args.max_p99_ms,
                        "max_latency_ms": args.max_latency_ms,
                        "min_rps": args.min_rps,
                        "max_queue_full_rate": args.max_queue_full_rate,
                    },
                    "observed": {
                        "fail_rate": round(fail_rate, 6),
                        "queue_full_rate": round(queue_full_rate, 6),
                        "p95_ms": p95,
                        "p99_ms": p99,
                        "max_latency_ms": max_latency,
                        "rps": rps_value,
                    },
                    "reasons": gate_reasons,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"report_json: {report_path}")

    if args.gate:
        return 0 if gate_passed else 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
