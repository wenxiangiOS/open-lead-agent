#!/usr/bin/env python3
"""运行真实 AI 场景回归测试。"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.real_ai.scenario_runner import RealAIScenarioRunner, ScenarioLoader, ScenarioValidationError


RUN_PROFILES = {
    "smoke": {"tags": ["smoke"]},
    "critical": {"tags": ["critical"]},
    "full": {},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行真实 AI 多轮场景回归测试")
    parser.add_argument(
        "--scenario-file",
        default=str(PROJECT_ROOT / "tests/real_ai/scenarios"),
        help="场景文件路径（JSON）或场景目录",
    )
    parser.add_argument(
        "--category",
        help="仅运行指定分类",
    )
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="仅运行包含指定 tag 的场景，可传多次",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help="仅运行指定场景，可传多次",
    )
    parser.add_argument(
        "--report-dir",
        default=str(PROJECT_ROOT / "reports/real_ai"),
        help="报告输出目录",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="只列出场景，不执行",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="遇到失败场景立即停止",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        help="最多运行前 N 个筛选后的场景",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="打乱筛选后的场景顺序",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="配合 --shuffle 使用的随机种子，默认 42",
    )
    parser.add_argument(
        "--rerun-failed-from",
        default=str(PROJECT_ROOT / "reports/real_ai/latest.json"),
        help="从历史报告里读取失败场景并重跑，默认 reports/real_ai/latest.json",
    )
    parser.add_argument(
        "--rerun-failed",
        action="store_true",
        help="只重跑历史报告里失败的场景",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(RUN_PROFILES.keys()),
        help="使用预置运行配置，如 smoke / critical / full",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="只校验场景定义，不执行",
    )
    parser.add_argument(
        "--require-tags",
        action="store_true",
        help="校验时将缺失 tags 视为错误",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="实时打印每轮用户输入、AI 回复和已收集信息",
    )
    return parser.parse_args()


def apply_filters(scenarios, args):
    if args.category:
        scenarios = [item for item in scenarios if item.category == args.category]
    if args.tags:
        required = set(args.tags)
        scenarios = [item for item in scenarios if required.issubset(set(item.tags))]
    if args.scenario_ids:
        allowed = set(args.scenario_ids)
        scenarios = [item for item in scenarios if item.scenario_id in allowed]
    if args.rerun_failed:
        failed_ids = load_failed_ids(args.rerun_failed_from)
        scenarios = [item for item in scenarios if item.scenario_id in failed_ids]
    if args.shuffle:
        rng = random.Random(args.seed)
        scenarios = list(scenarios)
        rng.shuffle(scenarios)
    if args.max_scenarios is not None:
        scenarios = scenarios[: args.max_scenarios]
    return scenarios


def apply_profile(args: argparse.Namespace) -> argparse.Namespace:
    if not args.profile:
        return args

    profile = RUN_PROFILES[args.profile]
    if profile.get("tags") and not args.tags:
        args.tags = list(profile["tags"])
    return args


def load_failed_ids(report_path: str):
    path = Path(report_path)
    if not path.exists():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["scenario_id"]
        for item in raw.get("results", [])
        if not item.get("passed", False)
    }


def _compact_text(text: str, limit: int = 120) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _compact_collected_info(collected_info) -> str:
    if not collected_info:
        return "-"
    parts = []
    for key, value in collected_info.items():
        if value not in (None, "", "未留", "未留称呼"):
            parts.append(f"{key}={value}")
    return ", ".join(parts) if parts else "-"


def _print_failure_transcript(result):
    print("  -> transcript:")
    for turn in result.turns:
        print(f"     U{turn.index}: {_compact_text(turn.user_message, 200)}")
        print(f"     A{turn.index}: {_compact_text(turn.assistant_response, 200)}")
        print(f"     I{turn.index}: {_compact_collected_info(turn.collected_info)}")


def print_progress(event, scenario, index, total, result, verbose=False):
    if event == "start":
        print(f"[{index}/{total}] RUN {scenario.scenario_id} ({scenario.category})")
        if scenario.description:
            print(f"       {scenario.description}")
        return

    if event == "turn" and result is not None and verbose:
        print(f"  U{result.index}: {_compact_text(result.user_message, 200)}")
        print(f"  A{result.index}: {_compact_text(result.assistant_response, 200)}")
        print(f"  I{result.index}: {_compact_collected_info(result.collected_info)}")
        return

    if event == "finish" and result is not None:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{index}/{total}] {status} {scenario.scenario_id} ({result.duration_seconds:.2f}s)")
        if result.failures:
            first_failure = result.failures[0]
            print(f"  -> [{first_failure.assertion_type}] {first_failure.message}")
            _print_failure_transcript(result)


async def main() -> int:
    args = parse_args()
    args = apply_profile(args)
    loader = ScenarioLoader(args.scenario_file)

    if args.validate:
        result = loader.validate(require_tags=args.require_tags)
        if result["errors"]:
            print("场景校验失败:")
            for item in result["errors"]:
                print(f"- {item}")
            return 1
        print("场景校验通过")
        if result["warnings"]:
            print("警告:")
            for item in result["warnings"]:
                print(f"- {item}")
        return 0

    try:
        scenarios = loader.load()
    except ScenarioValidationError as exc:
        print(f"场景加载失败: {exc}")
        return 1
    scenarios = apply_filters(scenarios, args)

    if args.list:
        for item in scenarios:
            tags = ",".join(item.tags) if item.tags else "-"
            print(f"{item.scenario_id}\t{item.category}\t{tags}\t{item.description}")
        return 0

    runner = RealAIScenarioRunner(
        scenario_file=args.scenario_file,
        report_dir=args.report_dir,
    )

    def progress(event, scenario, index, total, result):
        print_progress(event, scenario, index, total, result, verbose=args.verbose)

    report = await runner.run(
        scenario_ids=[item.scenario_id for item in scenarios],
        stop_on_failure=args.stop_on_failure,
        progress_callback=progress,
    )

    summary = report["summary"]
    print(f"总场景: {summary['total']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"总耗时: {summary['total_duration_seconds']}s")
    print(f"平均耗时: {summary['avg_duration_seconds']}s")
    print(f"最长耗时: {summary['max_duration_seconds']}s")
    print(f"Token: {summary['token_usage']['total_tokens']} (调用 {summary['token_usage']['call_count']} 次)")

    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        tags = ",".join(result.get("tags", [])) or "-"
        print(f"[{status}] {result['scenario_id']} ({result['category']}, tags={tags})")
        for failure in result["failures"]:
            turn_label = f"turn={failure['turn']}" if failure.get("turn") else "turn=-"
            print(f"  - [{failure['assertion_type']}] {turn_label} {failure['message']}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
