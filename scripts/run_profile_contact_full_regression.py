#!/usr/bin/env python3
"""
运行 05_PROFILE_COLLECTION_STRATEGY.md + 06_CONTACT_COLLECTION.md 完整方案的真实 AI 回归。

覆盖范围：
1. tests/real_ai/scenarios/*.json 中所有非 mq chat 场景
2. tests/integration/test_contact_collection_integration.py 中 21 个联系方式集成场景

用途：
- 验证资料收集主策略（05）是否正确
- 验证联系方式状态机（06）是否正确
- 验证两者交接时的真实 AI 效果是否符合预期
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_SCENARIOS_DIR = PROJECT_ROOT / "tests" / "real_ai" / "scenarios"
CHAT_RUNNER = PROJECT_ROOT / "scripts" / "run_real_ai_regression.py"
CONTACT_RUNNER = PROJECT_ROOT / "tests" / "integration" / "test_contact_collection_integration.py"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "real_ai" / "profile_contact_full"
CONTACT_SCENARIO_COUNT = 21
CORE84_CHAT_SCENARIO_IDS = [
    "policy_core_field_priority_over_quasi",
    "policy_quasi_core_marital_status_once_only",
    "policy_core_field_twice_max",
    "policy_medium_field_once_max",
    "policy_multi_field_extract_single_sentence",
    "policy_contact_trigger_insufficient_fields",
    "policy_contact_trigger_sufficient_fields",
    "policy_faq_answer_then_resume",
    "policy_reception_before_ask",
    "policy_transition_between_fields",
    "policy_first_turn_greeting_ack",
    "policy_cooldown_no_consecutive_same_field",
    "policy_income_soft_ask",
    "policy_partner_requirement_continuous_extract",
    "policy_emotion_defensive_explain",
    "policy_memory_reuse_location",
    "policy_memory_reuse_preference",
    "policy_low_info_huitouzaishuo_pause",
    "policy_mixed_answer_and_faq",
    "policy_opening_location_occupation_prefers_low_pressure_core",
    "policy_opening_location_occupation_fee_answers_first",
    "policy_latest_location_followup_prefers_occupation",
    "policy_mixed_location_and_boundary",
    "field_multi_info_extract_basic",
    "field_partner_requirement_should_not_override_location",
    "field_education_extract_master",
    "field_occupation_extract_programmer",
    "field_greeting_should_not_fill_profile",
    "field_marital_status_divorced",
    "field_income_extract_monthly",
    "field_conflict_partner_requirement_change_once",
    "faq_priority_fee",
    "faq_priority_contact_why_phone",
    "faq_priority_store_location",
    "faq_priority_how_match",
    "faq_priority_can_add_wechat",
    "faq_priority_photo_request",
    "faq_priority_reliable",
    "faq_priority_safety",
    "listener_first_greeting_probe_intent",
    "listener_first_zaima_probe_intent",
    "listener_first_unstable_opening_clarify_probe_intent",
    "listener_first_opening_clarify_then_soft_intent_self_intro",
    "listener_first_opening_probe_particle_soft_intent_self_intro",
    "listener_first_opening_probe_xiankan_soft_intent_self_intro",
    "listener_first_opening_probe_wenwen_qingkuang_prefix_self_intro",
    "listener_first_opening_faq_does_not_collect_fields",
    "listener_first_opening_boundary_contact_refusal_no_push",
    "listener_first_opening_profile_provided_no_repeat_field",
    "listener_first_opening_mixed_faq_priority_over_matchmaking",
    "listener_first_opening_mixed_boundary_priority_over_profile",
    "listener_first_explicit_matchmaking_enters_mainline",
    "listener_first_explicit_matchmaking_allows_open_self_intro",
    "listener_first_multi_profile_no_mechanical_repeat",
    "listener_first_matchmaking_then_multi_profile_stays_contextual",
    "listener_first_preference_ack_city",
    "listener_first_mixed_answer_and_fee",
    "listener_first_boundary_ack_before_pause",
    "listener_first_boundary_opening_no_collection",
    "listener_first_latest_location_prefers_occupation",
    "listener_first_reliability_then_answer",
    "listener_first_privacy_then_answer",
    "listener_first_mixed_answer_and_boundary",
    "humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot",
    "humanlike_resume_profile_collection_does_not_jump_to_contact",
    "humanlike_phone_refusal_wechat_followup_has_complete_sentence",
    "humanlike_transition_natural_field_switch",
    "humanlike_transition_with_feedback",
    "humanlike_memory_reuse_occupation",
    "humanlike_emotion_recognition_defensive_explanation",
    "humanlike_ask_limit_core_field_2_times",
    "humanlike_ask_limit_medium_field_1_time",
    "humanlike_no_consecutive_same_field_ask",
    "humanlike_answer_question_then_resume",
    "humanlike_no_large_repeat_profile",
    "matchmaker_boundary_not_convenient_field",
    "matchmaker_boundary_questioned_too_much",
    "matchmaker_boundary_topic_shift_before_data",
    "matchmaker_mixed_answer_fee",
    "matchmaker_mixed_contact_fee",
    "matchmaker_mixed_preference_reliability",
    "ending_divorce_incomplete_should_end",
    "ending_both_contact_refused",
    "ending_normal_complete",
]
SCENARIO_PACKS = {
    "core84": {
        "description": "05 + 06 完整方案核心场景包（历史名称 core84）：84 个 chat 核心场景 + 21 个联系方式集成场景",
        "chat_scenario_ids": CORE84_CHAT_SCENARIO_IDS,
        "include_contact_suite": True,
    }
}


def _count_chat_scenarios() -> int:
    total = 0
    for file_path in sorted(CHAT_SCENARIOS_DIR.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        total += len(data.get("scenarios", []))
    return total


def _scenario_pack_total(pack_name: str) -> int:
    pack = SCENARIO_PACKS[pack_name]
    return len(pack["chat_scenario_ids"]) + (CONTACT_SCENARIO_COUNT if pack["include_contact_suite"] else 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 05_PROFILE_COLLECTION_STRATEGY.md + 06_CONTACT_COLLECTION.md 完整方案真实 AI 回归"
    )
    parser.add_argument("--verbose", action="store_true", help="透传详细输出给下游 runner")
    parser.add_argument("--stop-on-failure", action="store_true", help="任一步失败即停止")
    parser.add_argument(
        "--scenario-pack",
        choices=sorted(SCENARIO_PACKS.keys()),
        default=None,
        help="运行预置场景包；core84 为历史名称，当前表示只运行完整方案核心场景包",
    )
    parser.add_argument("--skip-chat", action="store_true", help="跳过 tests/real_ai/scenarios/*.json 场景")
    parser.add_argument("--skip-contact", action="store_true", help="跳过 21 个联系方式集成场景")
    parser.add_argument(
        "--contact-scenario",
        type=str,
        default=None,
        help="只跑单个联系方式场景，如 1.1 / 2.4 / 3.8",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="报告输出目录；chat runner 报告输出到该目录下的 chat/ 子目录",
    )
    parser.add_argument("--list", action="store_true", help="只列出覆盖范围，不执行")
    return parser.parse_args()


def print_coverage() -> None:
    chat_count = _count_chat_scenarios()
    total = chat_count + CONTACT_SCENARIO_COUNT
    print("=" * 78)
    print("05_PROFILE_COLLECTION_STRATEGY.md + 06_CONTACT_COLLECTION.md 完整方案真实 AI 回归")
    print("=" * 78)
    print(f"chat 场景目录: {CHAT_SCENARIOS_DIR}")
    print(f"chat 场景数: {chat_count}")
    print(f"联系方式集成场景数: {CONTACT_SCENARIO_COUNT}")
    print(f"总覆盖执行数（不含变体）: {total}")
    print()
    print("执行内容：")
    print("1. tests/real_ai/scenarios/*.json 中全部非 mq chat 场景")
    print("2. tests/integration/test_contact_collection_integration.py 中 21 个真实 AI 联系方式场景")
    print()
    print("执行命令示例：")
    print("  python3 scripts/run_profile_contact_full_regression.py --verbose")
    print("  python3 scripts/run_profile_contact_full_regression.py --scenario-pack core84 --verbose")
    print("  python3 scripts/run_profile_contact_full_regression.py --contact-scenario 1.1 --skip-chat")
    print()
    print("预置场景包：")
    for pack_name, pack in SCENARIO_PACKS.items():
        print(f"  - {pack_name}: {_scenario_pack_total(pack_name)} 场景 | {pack['description']}")
    print("=" * 78)


def run_command(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}\n")
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode


def write_summary(report_dir: Path, chat_code: int | None, contact_code: int | None) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "latest_summary.md"
    lines = [
        "# 完整方案真实 AI 回归汇总",
        "",
        f"- 时间: {datetime.now().isoformat(timespec='seconds')}",
        "- 方案文档: `docs/05_PROFILE_COLLECTION_STRATEGY.md` + `docs/06_CONTACT_COLLECTION.md`",
        f"- chat 场景目录: `{CHAT_SCENARIOS_DIR}`",
        f"- chat 场景数: `{_count_chat_scenarios()}`",
        f"- 联系方式集成场景数: `{CONTACT_SCENARIO_COUNT}`",
        f"- chat runner 退出码: `{chat_code}`" if chat_code is not None else "- chat runner: `SKIPPED`",
        f"- contact runner 退出码: `{contact_code}`" if contact_code is not None else "- contact runner: `SKIPPED`",
        "",
        "## 执行说明",
        "",
        "这份汇总对应的测试目标是：",
        "",
        "1. 验证 05_PROFILE_COLLECTION_STRATEGY.md 中的资料主线、Gate、恢复、冻结与成本控制规则。",
        "2. 验证 06_CONTACT_COLLECTION.md 中的电话/微信状态机、拒绝检测、香港/非香港分支与结束条件。",
        "3. 验证两份方案联动后的真实 AI 效果，而不是只测单独模块。",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[summary] 已写入 {summary_path}")


def main() -> int:
    args = parse_args()

    if args.list:
        print_coverage()
        return 0

    report_dir = Path(args.report_dir).resolve()
    chat_report_dir = report_dir / "chat"

    print_coverage()

    chat_code: int | None = None
    contact_code: int | None = None
    pack = SCENARIO_PACKS.get(args.scenario_pack) if args.scenario_pack else None

    if not args.skip_chat:
        chat_cmd = [
            sys.executable,
            str(CHAT_RUNNER),
            "--scenario-file",
            str(CHAT_SCENARIOS_DIR),
            "--report-dir",
            str(chat_report_dir),
        ]
        if pack:
            for scenario_id in pack["chat_scenario_ids"]:
                chat_cmd.extend(["--scenario-id", scenario_id])
        if args.verbose:
            chat_cmd.append("--verbose")
        if args.stop_on_failure:
            chat_cmd.append("--stop-on-failure")
        chat_code = run_command(chat_cmd)
        if chat_code != 0 and args.stop_on_failure:
            write_summary(report_dir, chat_code, contact_code)
            return chat_code

    should_run_contact = not args.skip_contact and (not pack or pack["include_contact_suite"])
    if should_run_contact:
        contact_cmd = [
            sys.executable,
            str(CONTACT_RUNNER),
            "--real-ai",
        ]
        if args.contact_scenario:
            contact_cmd.extend(["--scenario", args.contact_scenario])
        contact_code = run_command(contact_cmd)
        if contact_code != 0 and args.stop_on_failure:
            write_summary(report_dir, chat_code, contact_code)
            return contact_code

    write_summary(report_dir, chat_code, contact_code)

    if chat_code not in {None, 0}:
        return chat_code
    if contact_code not in {None, 0}:
        return contact_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
