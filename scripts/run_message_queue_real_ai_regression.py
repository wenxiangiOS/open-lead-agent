#!/usr/bin/env python3
"""
运行 07_MESSAGE_QUEUE_DESIGN.md 已实现方案的真实 AI 回归。

覆盖范围：
1. 连发/多消息承接的人味化场景
2. 多字段连发后的上下文续接
3. 连发后的单主问题推进与冷却保护

用途：
- 验证 MQ 文档已落地方案在真实 AI 回复下的最终效果
- 只看真实对话内容，不串行附带 mq ingest runner
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_RUNNER = PROJECT_ROOT / "scripts" / "run_real_ai_regression.py"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "real_ai" / "message_queue_real_ai"

MQ_REAL_AI_CORE_SCENARIO_IDS = [
    "field_multi_sentence_extract",
    "policy_opening_multi_field_shadow_profile_skips_location_age",
    "listener_first_multi_profile_no_mechanical_repeat",
    "listener_first_matchmaking_then_multi_profile_stays_contextual",
    "humanlike_no_repeat_age_question_within_cooldown",
    "humanlike_no_premature_skip_without_explicit_refusal",
    "humanlike_burst_input_preference_and_city_captured_first_reply",
    "humanlike_single_main_question_per_turn_after_burst",
    "humanlike_skip_guard_enabled_debug_info_not_show_skip",
    "humanlike_cooldown_then_field_can_be_asked_again",
]

SCENARIO_PACKS = {
    "core10": {
        "description": "07_MESSAGE_QUEUE_DESIGN.md 已实现方案核心真实 AI 场景包",
        "scenario_ids": MQ_REAL_AI_CORE_SCENARIO_IDS,
    }
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 07_MESSAGE_QUEUE_DESIGN.md 已实现方案真实 AI 回归"
    )
    parser.add_argument(
        "--scenario-pack",
        choices=sorted(SCENARIO_PACKS.keys()),
        default="core10",
        help="运行预置场景包；默认 core10",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help="额外指定单个场景；可传多次。若传入则只运行这些场景。",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="报告输出目录",
    )
    parser.add_argument("--verbose", action="store_true", help="透传详细输出给 chat runner")
    parser.add_argument("--stop-on-failure", action="store_true", help="任一步失败即停止")
    parser.add_argument("--list", action="store_true", help="只列出覆盖范围，不执行")
    return parser.parse_args()


def selected_scenarios(args: argparse.Namespace) -> list[str]:
    if args.scenario_ids:
        return list(args.scenario_ids)
    pack = SCENARIO_PACKS[args.scenario_pack]
    return list(pack["scenario_ids"])


def print_coverage(args: argparse.Namespace) -> None:
    ids = selected_scenarios(args)
    print("=" * 78)
    print("07_MESSAGE_QUEUE_DESIGN.md 真实 AI 回归")
    print("=" * 78)
    print(f"场景包: {args.scenario_pack}")
    print(f"场景数: {len(ids)}")
    print(f"报告目录: {args.report_dir}")
    print()
    print("覆盖目标：")
    print("1. 连发输入后的首轮承接是否自然")
    print("2. 多字段/多句输入后是否不回头机械重问")
    print("3. 连发后是否尽量只推进一个主问题")
    print("4. 同字段冷却、skip guard 等队列相关体验是否生效")
    print()
    print("场景清单：")
    for scenario_id in ids:
        print(f"- {scenario_id}")
    print("=" * 78)


def write_summary(report_dir: Path, exit_code: int, scenario_ids: list[str]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "latest_summary.md"
    lines = [
        "# 07_MESSAGE_QUEUE_DESIGN.md 真实 AI 回归汇总",
        "",
        f"- 时间: {datetime.now().isoformat(timespec='seconds')}",
        "- 方案文档: `docs/07_MESSAGE_QUEUE_DESIGN.md`",
        f"- 场景数: `{len(scenario_ids)}`",
        f"- runner 退出码: `{exit_code}`",
        "",
        "## 场景清单",
        "",
    ]
    lines.extend(f"- `{scenario_id}`" for scenario_id in scenario_ids)
    lines.append("")
    lines.append("## 执行命令")
    lines.append("")
    lines.append("```bash")
    lines.append(
        "python3 scripts/run_message_queue_real_ai_regression.py --scenario-pack core10 --verbose"
    )
    lines.append("```")
    lines.append("")
    lines.append("报告详见同目录下 `latest.json` / `latest.md`（由 chat runner 生成）。")
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    scenario_ids = selected_scenarios(args)
    if args.list:
        print_coverage(args)
        return 0

    report_dir = Path(args.report_dir)
    cmd = [
        sys.executable,
        str(CHAT_RUNNER),
        "--report-dir",
        str(report_dir),
    ]
    if args.verbose:
        cmd.append("--verbose")
    if args.stop_on_failure:
        cmd.append("--stop-on-failure")
    for scenario_id in scenario_ids:
        cmd.extend(["--scenario-id", scenario_id])

    print(f"\n$ {' '.join(cmd)}\n")
    exit_code = subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode
    write_summary(report_dir, exit_code, scenario_ids)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
