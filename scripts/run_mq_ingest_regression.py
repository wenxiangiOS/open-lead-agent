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


def _default_payload(message: str, scenario_id: str, step: int, account_id: str, run_id: str) -> dict[str, Any]:
    return {
        "accountId": account_id,
        "dialogId": f"d_{scenario_id}_{run_id}",
        "message": message,
        "platformMsgId": f"{scenario_id}_{step}_{run_id}",
        "timestamp": str(int(time.time() * 1000)),
    }


def _normalize_expected_list(value: Any, size: int) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value] * size


def _normalize_allowed_list(value: Any, size: int) -> list[list[str]]:
    if not isinstance(value, list):
        return [[str(value)] for _ in range(size)]
    if value and all(not isinstance(item, list) for item in value):
        return [[str(item) for item in value] for _ in range(size)]
    normalized: list[list[str]] = []
    for item in value:
        if isinstance(item, list):
            normalized.append([str(v) for v in item])
        else:
            normalized.append([str(item)])
    return normalized


def _evaluate_result(responses: list[dict[str, Any]], mq_expect: dict[str, Any]) -> tuple[bool, str]:
    statuses = [str(item.get("status", "")) for item in responses]
    accepted_flags = [bool(item.get("accepted", False)) for item in responses]
    session_states = [str(item.get("sessionState", "")) for item in responses]
    cancel_like_flags = [bool(item.get("cancelLike", False)) for item in responses]
    force_flush_flags = [bool(item.get("forceFlush", False)) for item in responses]
    pending_values = [int(item.get("pending", 0) or 0) for item in responses]
    seq_values = [int(item.get("seq", 0) or 0) for item in responses]

    expected_statuses = mq_expect.get("expected_statuses")
    expected_statuses_any = mq_expect.get("expected_statuses_any")
    must_contain_status = mq_expect.get("must_contain_status")
    expected_accepted = mq_expect.get("expected_accepted")
    expected_session_states = mq_expect.get("expected_session_states")
    expected_cancel_like = mq_expect.get("expected_cancel_like")
    expected_force_flush = mq_expect.get("expected_force_flush")
    pending_min = mq_expect.get("expected_pending_min")
    pending_max = mq_expect.get("expected_pending_max")
    expect_seq_strictly_increasing = bool(mq_expect.get("expect_seq_strictly_increasing", False))

    if expected_statuses is not None:
        expected_statuses_list = _normalize_expected_list(expected_statuses, len(statuses))
        if list(expected_statuses_list) != statuses:
            return False, f"status mismatch: expected={expected_statuses_list}, actual={statuses}"

    if expected_statuses_any is not None:
        expected_any_list = _normalize_allowed_list(expected_statuses_any, len(statuses))
        if len(expected_any_list) != len(statuses):
            return False, f"expected_statuses_any size mismatch: expected={len(statuses)}, actual={len(expected_any_list)}"
        for idx, (actual, allowed) in enumerate(zip(statuses, expected_any_list), start=1):
            if actual not in allowed:
                return False, f"status_any mismatch at step {idx}: allowed={allowed}, actual={actual}"

    if must_contain_status is not None:
        required_statuses = [str(must_contain_status)] if not isinstance(must_contain_status, list) else [str(v) for v in must_contain_status]
        missing = [status for status in required_statuses if status not in statuses]
        if missing:
            return False, f"must_contain_status missing={missing}, actual={statuses}"

    if expected_accepted is not None:
        expected_accepted_list = [bool(v) for v in _normalize_expected_list(expected_accepted, len(accepted_flags))]
        if list(expected_accepted_list) != accepted_flags:
            return False, f"accepted mismatch: expected={expected_accepted_list}, actual={accepted_flags}"

    if expected_session_states is not None:
        expected_states_list = [str(v) for v in _normalize_expected_list(expected_session_states, len(session_states))]
        if list(expected_states_list) != session_states:
            return False, f"sessionState mismatch: expected={expected_states_list}, actual={session_states}"

    if expected_cancel_like is not None:
        expected_cancel_like_list = [bool(v) for v in _normalize_expected_list(expected_cancel_like, len(cancel_like_flags))]
        if list(expected_cancel_like_list) != cancel_like_flags:
            return False, f"cancelLike mismatch: expected={expected_cancel_like_list}, actual={cancel_like_flags}"

    if expected_force_flush is not None:
        expected_force_flush_list = [bool(v) for v in _normalize_expected_list(expected_force_flush, len(force_flush_flags))]
        if list(expected_force_flush_list) != force_flush_flags:
            return False, f"forceFlush mismatch: expected={expected_force_flush_list}, actual={force_flush_flags}"

    if pending_min is not None:
        expected_pending_min = [int(v) for v in _normalize_expected_list(pending_min, len(pending_values))]
        for idx, (actual, minimum) in enumerate(zip(pending_values, expected_pending_min), start=1):
            if actual < minimum:
                return False, f"pending min mismatch at step {idx}: expected>={minimum}, actual={actual}"

    if pending_max is not None:
        expected_pending_max = [int(v) for v in _normalize_expected_list(pending_max, len(pending_values))]
        for idx, (actual, maximum) in enumerate(zip(pending_values, expected_pending_max), start=1):
            if actual > maximum:
                return False, f"pending max mismatch at step {idx}: expected<={maximum}, actual={actual}"

    if expect_seq_strictly_increasing and len(seq_values) >= 2:
        for idx in range(1, len(seq_values)):
            if seq_values[idx] <= seq_values[idx - 1]:
                return False, f"seq not strictly increasing at step {idx + 1}: actual={seq_values}"

    return True, "ok"


def _render_payload_template(raw_payload: Any, context: dict[str, Any]) -> Any:
    if isinstance(raw_payload, dict):
        return {k: _render_payload_template(v, context) for k, v in raw_payload.items()}
    if isinstance(raw_payload, list):
        return [_render_payload_template(v, context) for v in raw_payload]
    if isinstance(raw_payload, str):
        rendered = raw_payload
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered
    return raw_payload


def _namespace_payload(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    namespaced = dict(payload)
    if "accountId" in namespaced and str(namespaced.get("accountId") or "").strip():
        namespaced["accountId"] = f"{str(namespaced['accountId']).strip()}_{run_id}"
    if "dialogId" in namespaced and str(namespaced.get("dialogId") or "").strip():
        namespaced["dialogId"] = f"{str(namespaced['dialogId']).strip()}_{run_id}"
    if "platformMsgId" in namespaced and str(namespaced.get("platformMsgId") or "").strip():
        namespaced["platformMsgId"] = f"{str(namespaced['platformMsgId']).strip()}_{run_id}"
    return namespaced


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

    run_id = uuid.uuid4().hex[:8]
    default_account_id = f"mq_reg_{scenario_id}_{run_id}"
    messages = scenario.get("messages", [])
    repeat_times = int(scenario.get("repeat_times", 1) or 1)
    if repeat_times > 1 and len(messages) == 1:
        messages = messages * repeat_times

    payloads = scenario.get("ingest_payloads")
    if payloads:
        rendered_payloads: list[dict[str, Any]] = []
        for step, payload in enumerate(payloads, start=1):
            context = {
                "RUN_ID": run_id,
                "SCENARIO_ID": scenario_id,
                "STEP": step,
                "ACCOUNT_ID": default_account_id,
            }
            rendered_payload = _render_payload_template(payload, context)
            if isinstance(rendered_payload, dict):
                rendered_payloads.append(_namespace_payload(rendered_payload, run_id))
        payloads = rendered_payloads
    else:
        payloads = [
            _default_payload(str(message or ""), scenario_id, i, default_account_id, run_id)
            for i, message in enumerate(messages, start=1)
        ]

    responses: list[dict[str, Any]] = []
    for step, payload in enumerate(payloads, start=1):
        try:
            http_status, body = _http_json("POST", ingest_url, payload, headers, args.timeout_seconds)
        except Exception as exc:
            duration = round(time.time() - started, 2)
            print(f"[{index}/{total}] FAIL {scenario_id} ({duration:.2f}s)")
            return MQScenarioResult(
                scenario_id=scenario_id,
                category=category,
                tags=tags,
                passed=False,
                skipped=False,
                duration_seconds=duration,
                message=f"request_error step={step}: {exc}",
            )
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
