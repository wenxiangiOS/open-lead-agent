#!/usr/bin/env python3
"""运行 MQ ingest API 回归（真实走 /api/xiaohongshu/messages/ingest）。"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class MQScenarioResult:
    scenario_id: str
    category: str
    tags: list[str]
    passed: bool
    skipped: bool
    duration_seconds: float
    message: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 MQ ingest API 回归测试")
    parser.add_argument(
        "--scenario-file",
        default=str(PROJECT_ROOT / "tests/real_ai/scenarios_pending/mq_regression.json"),
        help="场景文件路径（JSON）或目录",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="服务地址，例如 http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="可选 X-API-Key",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help="仅运行指定场景，可传多次",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        help="最多运行前 N 个筛选后的场景",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=8.0,
        help="每次 HTTP 请求超时秒数",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="只列出场景，不执行",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印每步 payload/response",
    )
    return parser.parse_args()


def _resolve_files(path: str) -> list[Path]:
    p = Path(path)
    if p.is_dir():
        return sorted(p.glob("*.json"))
    return [p]


def _load_mq_scenarios(path: str) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for file in _resolve_files(path):
        raw = json.loads(file.read_text(encoding="utf-8"))
        for item in raw.get("scenarios", []):
            if item.get("category") == "mq":
                scenarios.append(item)
    return scenarios


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
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


def _default_payload(message: str, scenario_id: str, step: int) -> dict[str, Any]:
    account_id = f"mq_reg_{scenario_id}_{uuid.uuid4().hex[:8]}"
    return {
        "accountId": account_id,
        "dialogId": f"d_{scenario_id}",
        "message": message,
        "platformMsgId": f"{scenario_id}_{step}_{uuid.uuid4().hex[:6]}",
        "timestamp": str(int(time.time() * 1000)),
    }


def _normalize_expected_list(value: Any, size: int) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value] * size


def _evaluate_result(responses: list[dict[str, Any]], mq_expect: dict[str, Any]) -> tuple[bool, str]:
    statuses = [str(item.get("status", "")) for item in responses]
    accepted_flags = [bool(item.get("accepted", False)) for item in responses]
    expected_statuses = mq_expect.get("expected_statuses")
    expected_accepted = mq_expect.get("expected_accepted")

    if expected_statuses is not None:
        expected_statuses_list = _normalize_expected_list(expected_statuses, len(statuses))
        if list(expected_statuses_list) != statuses:
            return False, f"status mismatch: expected={expected_statuses_list}, actual={statuses}"

    if expected_accepted is not None:
        expected_accepted_list = [bool(v) for v in _normalize_expected_list(expected_accepted, len(accepted_flags))]
        if list(expected_accepted_list) != accepted_flags:
            return False, f"accepted mismatch: expected={expected_accepted_list}, actual={accepted_flags}"

    return True, "ok"


def run_one(scenario: dict[str, Any], args: argparse.Namespace, index: int, total: int) -> MQScenarioResult:
    scenario_id = str(scenario.get("id"))
    category = str(scenario.get("category", ""))
    tags = list(scenario.get("tags", []))
    started = time.time()
    print(f"[{index}/{total}] RUN {scenario_id} ({category})")
    if scenario.get("description"):
        print(f"       {scenario['description']}")

    mq_expect = scenario.get("mq_expect")
    if not mq_expect:
        duration = round(time.time() - started, 2)
        msg = "missing mq_expect (placeholder scenario)"
        print(f"[{index}/{total}] SKIP {scenario_id} ({duration:.2f}s)")
        return MQScenarioResult(
            scenario_id=scenario_id,
            category=category,
            tags=tags,
            passed=True,
            skipped=True,
            duration_seconds=duration,
            message=msg,
        )

    ingest_url = f"{args.base_url.rstrip('/')}/api/xiaohongshu/messages/ingest"
    headers: dict[str, str] = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    payloads = scenario.get("ingest_payloads")
    if not payloads:
        messages = scenario.get("messages", [])
        payloads = [_default_payload(str(message or ""), scenario_id, i) for i, message in enumerate(messages, start=1)]

    responses: list[dict[str, Any]] = []
    for step, payload in enumerate(payloads, start=1):
        http_status, body = _http_json("POST", ingest_url, payload, headers, args.timeout_seconds)
        if args.verbose:
            print(f"  STEP{step} payload={payload}")
            print(f"  STEP{step} http={http_status} body={body}")
        if http_status != 200:
            duration = round(time.time() - started, 2)
            print(f"[{index}/{total}] FAIL {scenario_id} ({duration:.2f}s)")
            return MQScenarioResult(
                scenario_id=scenario_id,
                category=category,
                tags=tags,
                passed=False,
                skipped=False,
                duration_seconds=duration,
                message=f"http_status={http_status}, body={body}",
            )
        responses.append(body)

    ok, reason = _evaluate_result(responses, mq_expect)
    duration = round(time.time() - started, 2)
    if ok:
        print(f"[{index}/{total}] PASS {scenario_id} ({duration:.2f}s)")
    else:
        print(f"[{index}/{total}] FAIL {scenario_id} ({duration:.2f}s)")
    return MQScenarioResult(
        scenario_id=scenario_id,
        category=category,
        tags=tags,
        passed=ok,
        skipped=False,
        duration_seconds=duration,
        message=reason,
    )


def main() -> int:
    args = parse_args()
    scenarios = _load_mq_scenarios(args.scenario_file)
    if args.scenario_ids:
        allowed = set(args.scenario_ids)
        scenarios = [item for item in scenarios if item.get("id") in allowed]
    if args.max_scenarios is not None:
        scenarios = scenarios[: args.max_scenarios]

    if args.list:
        for item in scenarios:
            tags = ",".join(item.get("tags", [])) or "-"
            print(f"{item.get('id')}\t{item.get('category')}\t{tags}\t{item.get('description', '')}")
        return 0

    results: list[MQScenarioResult] = []
    for i, scenario in enumerate(scenarios, start=1):
        results.append(run_one(scenario, args, i, len(scenarios)))

    total = len(results)
    passed = sum(1 for r in results if r.passed and not r.skipped)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    total_duration = round(sum(r.duration_seconds for r in results), 3)
    avg_duration = round(total_duration / total, 3) if total else 0.0
    max_duration = round(max((r.duration_seconds for r in results), default=0.0), 3)

    print(f"总场景: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"跳过: {skipped}")
    print(f"总耗时: {total_duration}s")
    print(f"平均耗时: {avg_duration}s")
    print(f"最长耗时: {max_duration}s")

    for item in results:
        status = "SKIP" if item.skipped else ("PASS" if item.passed else "FAIL")
        tags = ",".join(item.tags) or "-"
        print(f"[{status}] {item.scenario_id} ({item.category}, tags={tags})")
        if item.message and (item.skipped or not item.passed):
            print(f"  - {item.message}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

